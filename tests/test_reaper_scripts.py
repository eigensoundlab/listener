# SPDX-License-Identifier: Apache-2.0
"""The REAPER actions of recording/reaper, run in Lua 5.4 against a small stand-in for REAPER's API.

This checks the scripts' logic and that they call nothing the stand-in does not know. It is not REAPER: the names and
signatures of the API functions are taken from REAPER's documentation, and an action still has to be tried there.
"""
import csv
import os

import pytest

lupa = pytest.importorskip("lupa")
from lupa import lua54  # noqa: E402

SCRIPTS = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "recording", "reaper")

MOCK = r"""
local S = { project_file = PROJECT, info = {}, info_str = {}, tracks = {}, items = {}, messages = {}, ext = {}, answer = nil }
local api = {}
function api.EnumProjects(idx) return {}, S.project_file end
function api.ShowMessageBox(text, title, kind) S.messages[#S.messages + 1] = text return 1 end
function api.Undo_BeginBlock() end
function api.Undo_EndBlock(name, flags) end
function api.UpdateArrange() end
function api.UpdateItemInProject(item) end
function api.TrackList_AdjustWindows(minor) end
function api.GetSetProjectInfo(proj, key, value, set) if set then S.info[key] = value end return S.info[key] or 0 end
function api.GetSetProjectInfo_String(proj, key, value, set) if set then S.info_str[key] = value end return true, S.info_str[key] or "" end
function api.CountTracks(proj) return #S.tracks end
function api.GetTrack(proj, i) return S.tracks[i + 1] end
function api.InsertTrackAtIndex(i, defaults) table.insert(S.tracks, i + 1, { name = "", v = {} }) end
function api.GetSetMediaTrackInfo_String(tr, key, value, set) assert(key == "P_NAME") if set then tr.name = value end return true, tr.name end
function api.SetMediaTrackInfo_Value(tr, key, value) tr.v[key] = value return true end
function api.CountMediaItems(proj) return #S.items end
function api.GetMediaItem(proj, i) return S.items[i + 1] end
function api.CountSelectedMediaItems(proj) local n = 0 for _, it in ipairs(S.items) do if it.selected then n = n + 1 end end return n end
function api.GetSelectedMediaItem(proj, i) local n = -1 for _, it in ipairs(S.items) do if it.selected then n = n + 1 if n == i then return it end end end end
function api.GetMediaItemInfo_Value(item, key) return assert(item.v[key], key) end
function api.GetActiveTake(item) return item.take end
function api.TakeIsMIDI(take) return false end
function api.GetSetMediaItemTakeInfo_String(take, key, value, set) assert(key == "P_NAME") if set then take.name = value end return true, take.name end
function api.GetMediaItemTakeInfo_Value(take, key) return assert(take.v[key], key) end
function api.GetMediaItemTake_Source(take) return take.source end
function api.PCM_Source_GetSectionInfo(src) return false, 0, 0, src.reversed or false end
function api.GetMediaSourceParent(src) return nil end
function api.GetMediaSourceFileName(src, buf) return src.file end
function api.TakeFX_GetCount(take) return take.fx or 0 end
function api.GetExtState(section, key) return S.ext[section .. key] or "" end
function api.SetExtState(section, key, value, persist) S.ext[section .. key] = value end
function api.GetUserInputs(title, n, captions, defaults) if S.answer then return true, S.answer end return false, "" end
reaper = setmetatable(api, { __index = function(_, k) error("the stand-in has no reaper." .. tostring(k)) end })
function item(name, pos, len, selected, extra)
  local it = { selected = selected, v = { D_POSITION = pos, D_LENGTH = len, D_FADEINLEN = 0, D_FADEOUTLEN = 0.02, D_VOL = 1 },
               take = { name = name, v = { D_STARTOFFS = pos, D_PLAYRATE = 1, D_VOL = 1 }, source = { file = "raw/rec-001.wav" } } }
  for k, v in pairs(extra or {}) do it.take[k] = v end
  S.items[#S.items + 1] = it
  return it
end
STATE = S
"""


def _lua(tmp_path, saved=True):
    lua = lua54.LuaRuntime(unpack_returned_tuples=True)
    lua.globals().PROJECT = str(tmp_path / "session.rpp") if saved else ""
    lua.execute(MOCK)
    return lua


def _run(lua, name):
    with open(os.path.join(SCRIPTS, name), encoding="utf-8") as fh:
        lua.execute(fh.read())


def test_set_up(tmp_path):
    lua = _lua(tmp_path)
    _run(lua, "Listener - Set up recording project.lua")
    s = lua.globals().STATE
    assert s.info["PROJECT_SRATE"] == 48000 and s.info["PROJECT_SRATE_USE"] == 1 and s.info_str["RECORD_PATH"] == "raw"
    track = s.tracks[1]
    assert track.name == "REC" and track.v["I_RECARM"] == 1 and track.v["I_RECINPUT"] == 0 and track.v["I_RECMON"] == 0
    _run(lua, "Listener - Set up recording project.lua")          # a second run adds no second track
    assert len(s.tracks) == 1
    unsaved = _lua(tmp_path, saved=False)
    _run(unsaved, "Listener - Set up recording project.lua")
    assert len(unsaved.globals().STATE.tracks) == 0 and "Save the project" in unsaved.globals().STATE.messages[1]


def test_name_takes_in_time_order_and_go_on_counting(tmp_path):
    lua = _lua(tmp_path)
    lua.execute('item("knock_medium_02", 1, 0.4, false) a = item("", 9, 0.4, true) b = item("", 5, 0.4, true) STATE.answer = "knock, medium"')
    _run(lua, "Listener - Name takes.lua")
    assert lua.eval("b.take.name") == "knock_medium_03" and lua.eval("a.take.name") == "knock_medium_04"
    lua.execute('STATE.answer = "door knock,hard"')
    _run(lua, "Listener - Name takes.lua")                           # a space in the id: refused, names unchanged
    assert lua.eval("b.take.name") == "knock_medium_03"


def test_export_take_list(tmp_path):
    lua = _lua(tmp_path)
    lua.execute('item("knock_medium_01", 1.5, 0.4, false) item("knock_hard_01", 3, 0.5, false, { fx = 1 }) item("untitled", 7, 1, false)')
    _run(lua, "Listener - Export take list.lua")
    with open(tmp_path / "takes.csv", newline="") as fh:
        rows = list(csv.DictReader(fh))
    assert [r["name"] for r in rows] == ["knock_hard_01", "knock_medium_01"]
    assert rows[1]["file"] == "raw/rec-001.wav" and float(rows[1]["start"]) == 1.5 and float(rows[1]["fade_out"]) == 0.02
    assert rows[0]["take_fx"] == "1" and float(rows[1]["gain_db"]) == 0
    from listener import takes
    assert takes.refusal(rows[0]) == "take FX" and takes.refusal(rows[1]) is None
    assert "1 items without a take name" in lua.eval("STATE.messages[#STATE.messages]")
