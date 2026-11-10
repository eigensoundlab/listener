-- @description Listener: export the take list (takes.csv) for cutting the raw recordings outside REAPER
-- @version 0.1.0
-- @author Daniel Sandner
-- @about
--   Writes takes.csv next to the project: for every named item (the selected ones, or all when none is selected) the
--   raw file it plays, where in that file, how long, and its fades. `listener takes takes.csv` then cuts the takes
--   from the raw files sample for sample, without REAPER's renderer: no gain, no resampling, no dither.
--   Items with a gain, a play rate, take FX or a reversed source are listed with what was found, and `listener takes`
--   refuses them: a take in the dataset is the recording as it was.

-- SPDX-License-Identifier: Apache-2.0
-- Copyright 2026 Daniel Sandner

local TITLE = "Listener: export take list"

local _, project_file = reaper.EnumProjects(-1)
if not project_file or project_file == "" then
  reaper.ShowMessageBox("Save the project first: takes.csv is written next to it.", TITLE, 0)
  return
end
local folder = project_file:match("^(.*)[/\\][^/\\]*$") or "."

local function root_source(take)
  local src = reaper.GetMediaItemTake_Source(take)
  local reversed = false
  while src do
    local ok, _, _, rev = reaper.PCM_Source_GetSectionInfo(src)
    if ok and rev then reversed = true end
    local parent = reaper.GetMediaSourceParent(src)
    if not parent then break end
    src = parent
  end
  return src, reversed
end

local function field(s)
  s = tostring(s)
  if s:find('[,"\n]') then s = '"' .. s:gsub('"', '""') .. '"' end
  return s
end

local function db(v) return v > 0 and 20 * math.log(v, 10) or -150 end

local use_selection = reaper.CountSelectedMediaItems(0) > 0
local count = use_selection and reaper.CountSelectedMediaItems(0) or reaper.CountMediaItems(0)
local rows, skipped = {}, 0
for i = 0, count - 1 do
  local item = use_selection and reaper.GetSelectedMediaItem(0, i) or reaper.GetMediaItem(0, i)
  local take = reaper.GetActiveTake(item)
  if take and not reaper.TakeIsMIDI(take) then
    local _, name = reaper.GetSetMediaItemTakeInfo_String(take, "P_NAME", "", false)
    if name:match("^[%w%-]+_[%w%-]+_%d+$") then
      local src, reversed = root_source(take)
      rows[#rows + 1] = {
        name = name,
        file = reaper.GetMediaSourceFileName(src, "") or "",
        start = reaper.GetMediaItemTakeInfo_Value(take, "D_STARTOFFS"),
        length = reaper.GetMediaItemInfo_Value(item, "D_LENGTH"),
        fade_in = reaper.GetMediaItemInfo_Value(item, "D_FADEINLEN"),
        fade_out = reaper.GetMediaItemInfo_Value(item, "D_FADEOUTLEN"),
        gain_db = db(reaper.GetMediaItemInfo_Value(item, "D_VOL") * reaper.GetMediaItemTakeInfo_Value(take, "D_VOL")),
        rate = reaper.GetMediaItemTakeInfo_Value(take, "D_PLAYRATE"),
        reversed = reversed and 1 or 0,
        take_fx = reaper.TakeFX_GetCount(take),
        position = reaper.GetMediaItemInfo_Value(item, "D_POSITION"),
      }
    else
      skipped = skipped + 1
    end
  end
end
if #rows == 0 then
  reaper.ShowMessageBox("No named takes found. Name them with \"Listener - Name takes\" (id_strength_number).", TITLE, 0)
  return
end
table.sort(rows, function(a, b) return a.name < b.name end)

local seen, doubles = {}, {}
for _, r in ipairs(rows) do
  if seen[r.name] then doubles[#doubles + 1] = r.name end
  seen[r.name] = true
end
if #doubles > 0 then
  reaper.ShowMessageBox("These names are used more than once:\n" .. table.concat(doubles, ", ") .. "\n\nNothing was written.", TITLE, 0)
  return
end

local path = folder .. "/takes.csv"
local out, why = io.open(path, "w")
if not out then
  reaper.ShowMessageBox("Could not write " .. path .. "\n" .. tostring(why), TITLE, 0)
  return
end
out:write("name,file,start,length,fade_in,fade_out,gain_db,rate,reversed,take_fx,position\n")
local changed = 0
for _, r in ipairs(rows) do
  if math.abs(r.gain_db) > 0.001 or math.abs(r.rate - 1) > 1e-9 or r.reversed == 1 or r.take_fx > 0 then changed = changed + 1 end
  out:write(table.concat({
    field(r.name), field(r.file), string.format("%.9f", r.start), string.format("%.9f", r.length),
    string.format("%.6f", r.fade_in), string.format("%.6f", r.fade_out), string.format("%.4f", r.gain_db),
    string.format("%.9f", r.rate), r.reversed, r.take_fx, string.format("%.6f", r.position) }, ",") .. "\n")
end
out:close()

reaper.ShowMessageBox(
  #rows .. " takes written to\n" .. path ..
  (skipped > 0 and ("\n\n" .. skipped .. " items without a take name of the form id_strength_number were left out.") or "") ..
  (changed > 0 and ("\n\n" .. changed .. " takes have a gain, a play rate, take FX or a reversed source: listener will refuse them until that is undone.") or "") ..
  "\n\nNext: listener takes takes.csv --session session.json --out takes", TITLE, 0)
