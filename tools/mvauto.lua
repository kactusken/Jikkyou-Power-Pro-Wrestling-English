-- Max Voltage autoplay rules for tools/mesen.py:
--   autoplay FRAMES tools/mvauto.lua [stop=YYYYMM] [step=PH:ST] [choice=1|2] [split=train|rest] [pages=1]
-- (step=2:19: stop when phase $11FA and step $11F8 reach those values, hex; pages=1: a screenshot
-- of every finished dialogue page, pNNNNN.png, logged as "page FRAME DATE start=PTR bank=BB" with
-- the script word the page started at ($1E76) and the bank override ($1E84: interviews))
-- Presses through the career: dialogue pages, the hub's PROCEED, the training split and the
-- show cards. It logs each change of (date, phase $11FA, step $11F8, hub screen $11D8) to
-- OUT/auto.log, takes a screenshot when nothing changes for 10 seconds, and stops (going on with
-- the next step) at the start of month `stop` (default 2001/04, i.e. never).
-- WRAM (from the code and dumps): $1FE2 year-1996, $1FE3 month, $11FA phase (0 = at the hub),
-- $11F8 step, $0088 career screen ($09 hub menu waiting, $0A a panel such as Profile, $15 the
-- training split), $11DA hub cursor (0-1 = PROCEED), $1E74 dialogue (3 / 7 = waiting for a button at the end of a page / line, 12 = a choice).
local last, still, pulse, plan, n = "", 0, 0, {}, 0
local lastdlg, dstill = -1, 0
local pstart, pages = nil, 0

local function key(api)
  return string.format("%d/%02d ph=%d st=%02X scr=%02X", 1996 + api.rb(0x1FE2), api.rb(0x1FE3),
    api.rw(0x11FA), api.rw(0x11F8), api.rb(0x88))
end

return function(f, api)
  local stop = tonumber(api.args.stop or "200104")
  local k = key(api)
  if k ~= last then api.log(f .. " " .. k); last = k; still = 0 else still = still + 1 end
  if (1996 + api.rb(0x1FE2)) * 100 + api.rb(0x1FE3) >= stop and api.rw(0x11FA) == 0 then return "stop" end
  if api.args.step then
    local ph, st = api.args.step:match("(%x+):(%x+)")
    if api.rw(0x11FA) == tonumber(ph, 16) and api.rw(0x11F8) == tonumber(st, 16) then return "stop" end
  end
  if #plan > 0 then                       -- a planned sequence: each button 6 frames down, 6 up
    pulse = pulse + 1
    if pulse <= 6 then return plan[1] end
    if pulse >= 12 then pulse = 0; table.remove(plan, 1) end
    return nil
  end
  if still > 0 and still % 600 == 0 then
    n = n + 1; api.shot(string.format("still%03d", n))
    api.log(f .. " still " .. k .. string.format(" dlg=%d", api.rb(0x1E74)))
  end
  if still >= 18000 then api.log(f .. " stuck: stop") return "stop" end   -- 5 minutes without a change
  local scr = api.rb(0x88)
  local dlg = api.rb(0x1E74)
  if dlg ~= lastdlg then
    if dlg == 0 then pstart = api.rw(0x1E76) end                  -- a page is about to be typed
    lastdlg = dlg; dstill = 0
  else dstill = dstill + 1 end
  if dlg == 3 or dlg == 7 then                                     -- dialogue waits for a button
    if dstill < 12 then return nil end                             -- (let the last tiles upload)
    local box = api.rw(0x1E78)                                     -- $A630/$B010 while the
    if api.args.pages == "1" and (box == 0xA630 or box == 0xB010) then   -- dialogue engine runs
      pages = pages + 1; api.shot(string.format("p%05d", pages))
      api.log(string.format("page %d %d/%02d p%05d start=%04X end=%04X bank=%02X", f, 1996 + api.rb(0x1FE2),
        api.rb(0x1FE3), pages, pstart or 0, api.rw(0x1E76), api.rb(0x1E84)))
    end
    pstart = nil
    plan = {{b = true}} return nil
  end
  if dlg == 12 and dstill == 20 then                      -- a choice: the first answer, or the second
    if api.args.choice == "2" then plan = {{down = true}, {b = true}} else plan = {{b = true}} end
    api.log(f .. " choice " .. (api.args.choice or "1"))
    return nil
  end
  if scr == 0x15 and still == 40 then        -- training split: points to W, S and R, then OK; or REST
    local R, D = {right = true}, {down = true}
    if api.args.split == "rest" then plan = {D, D, D, D, D, {b = true}}
    else plan = {R, R, R, R, R, D, R, R, R, R, R, D, R, R, R, R, R, R, D, {b = true}} end
    return nil
  end
  if scr == 0x0A and still == 40 then plan = {{b = true}} return nil end   -- a panel: close it
  if scr == 0x09 and still == 40 then                                      -- hub menu: PROCEED
    if api.rb(0x11DA) < 2 then plan = {{b = true}} else plan = {{left = true}, {b = true}} end
    return nil
  end
  if still > 120 and still % 90 == 0 then plan = {{b = true}} end       -- anything else: confirm
  return nil
end
