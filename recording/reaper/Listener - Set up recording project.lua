-- @description Listener: set up a recording project (48 kHz, one mono track on input 1, raw takes in their own folder)
-- @version 0.1.0
-- @author Daniel Sandner
-- @about
--   Prepares the saved project for recording raw sound-effect takes for the listener dataset: project sample rate
--   48 kHz, recordings into the folder "raw" next to the project, and one track "REC" armed on input 1 (mono) with
--   input monitoring off. It does not touch the recording format: the message at the end says what to check by hand.
--   See recording/README.md in https://github.com/eigensoundlab/listener

-- SPDX-License-Identifier: Apache-2.0
-- Copyright 2026 Daniel Sandner

local TITLE = "Listener: set up recording project"
local TRACK = "REC"

local _, project_file = reaper.EnumProjects(-1)
if not project_file or project_file == "" then
  reaper.ShowMessageBox("Save the project first (File > Save project as...), in the folder the session will live in.\nThen run this action again.", TITLE, 0)
  return
end

reaper.Undo_BeginBlock()
reaper.GetSetProjectInfo(0, "PROJECT_SRATE", 48000, true)
reaper.GetSetProjectInfo(0, "PROJECT_SRATE_USE", 1, true)
reaper.GetSetProjectInfo_String(0, "RECORD_PATH", "raw", true)

local track
for i = 0, reaper.CountTracks(0) - 1 do
  local t = reaper.GetTrack(0, i)
  local _, name = reaper.GetSetMediaTrackInfo_String(t, "P_NAME", "", false)
  if name == TRACK then track = t break end
end
if not track then
  local at = reaper.CountTracks(0)
  reaper.InsertTrackAtIndex(at, true)
  track = reaper.GetTrack(0, at)
  reaper.GetSetMediaTrackInfo_String(track, "P_NAME", TRACK, true)
end
reaper.SetMediaTrackInfo_Value(track, "I_RECINPUT", 0)   -- mono, the first hardware input
reaper.SetMediaTrackInfo_Value(track, "I_RECMODE", 0)    -- record the input
reaper.SetMediaTrackInfo_Value(track, "I_RECMON", 0)     -- no monitoring through REAPER: nothing reaches the loudspeakers
reaper.SetMediaTrackInfo_Value(track, "D_VOL", 1)
reaper.SetMediaTrackInfo_Value(track, "D_PAN", 0)
reaper.SetMediaTrackInfo_Value(track, "I_RECARM", 1)
reaper.TrackList_AdjustWindows(false)
reaper.UpdateArrange()
reaper.Undo_EndBlock(TITLE, -1)

reaper.ShowMessageBox(
  "Done: 48 kHz, recordings go to the folder \"raw\", track \"" .. TRACK .. "\" is armed on input 1 (mono), monitoring off.\n\n" ..
  "Check by hand, once:\n" ..
  "1. File > Project settings > Media: recording format WAV, 24 bit PCM.\n" ..
  "2. Options > Preferences > Audio > Device: the interface, 48000 Hz.\n" ..
  "3. No FX on the track or the master. Nothing that limits or levels the input, in REAPER or in the driver.\n" ..
  "4. Set the input gain so the hardest hit peaks between -12 and -6 dB, then leave the knob alone for that sound.\n" ..
  "5. Record 10 s of the silent room at the same gain: name that take roomtone_-_01.",
  TITLE, 0)
