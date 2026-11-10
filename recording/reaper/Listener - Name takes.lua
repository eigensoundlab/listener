-- @description Listener: name the selected items as takes of one sound (id_strength_number)
-- @version 0.1.0
-- @author Daniel Sandner
-- @about
--   Names the selected items, in time order, "<id>_<strength>_<two-digit number>": the id from the shot list
--   (recording/shotlist.csv), the strength (soft, medium, hard, or - for none). Numbers go on from the highest one
--   that the project already has for that id and strength. "Listener - Export take list.lua" reads these names.

-- SPDX-License-Identifier: Apache-2.0
-- Copyright 2026 Daniel Sandner

local TITLE = "Listener: name takes"

local n = reaper.CountSelectedMediaItems(0)
if n == 0 then
  reaper.ShowMessageBox("Select the items to name: the takes of one sound at one strength.", TITLE, 0)
  return
end
local last = reaper.GetExtState("listener", "name_takes")
local ok, answer = reaper.GetUserInputs(TITLE, 2, "Id (from the shot list),Strength (soft medium hard -)", last ~= "" and last or ",medium")
if not ok then return end
local id, strength = answer:match("^%s*([^,]-)%s*,%s*([^,]-)%s*$")
if not id or id == "" or not id:match("^[%w%-]+$") then
  reaper.ShowMessageBox("The id may hold letters, digits and hyphens only (no spaces, no underscores).", TITLE, 0)
  return
end
if strength == "" then strength = "-" end
if not strength:match("^[%w%-]+$") then
  reaper.ShowMessageBox("The strength may hold letters, digits and hyphens only.", TITLE, 0)
  return
end
reaper.SetExtState("listener", "name_takes", id .. "," .. strength, false)

local prefix = id .. "_" .. strength .. "_"
local selected, items = {}, {}
for i = 0, n - 1 do
  local item = reaper.GetSelectedMediaItem(0, i)
  selected[item] = true
  items[#items + 1] = { item = item, pos = reaper.GetMediaItemInfo_Value(item, "D_POSITION") }
end
table.sort(items, function(a, b) return a.pos < b.pos end)

local highest = 0
for i = 0, reaper.CountMediaItems(0) - 1 do
  local item = reaper.GetMediaItem(0, i)
  local take = not selected[item] and reaper.GetActiveTake(item)
  if take then
    local _, name = reaper.GetSetMediaItemTakeInfo_String(take, "P_NAME", "", false)
    if name:sub(1, #prefix) == prefix then
      local num = tonumber(name:sub(#prefix + 1):match("^(%d+)$"))
      if num and num > highest then highest = num end
    end
  end
end

reaper.Undo_BeginBlock()
local named = 0
for _, it in ipairs(items) do
  local take = reaper.GetActiveTake(it.item)
  if take then
    named = named + 1
    reaper.GetSetMediaItemTakeInfo_String(take, "P_NAME", prefix .. string.format("%02d", highest + named), true)
    reaper.UpdateItemInProject(it.item)
  end
end
reaper.UpdateArrange()
reaper.Undo_EndBlock(TITLE, -1)
