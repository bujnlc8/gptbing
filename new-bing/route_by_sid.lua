local headers = ngx.req.get_headers()
-- 先判断referer
local referer = headers['Referer']
if referer and not string.match(referer, 'https://servicewechat.com/wxee7496be5b68b740') then
    ngx.log(ngx.ERR, 'referer: ' .. referer)
    -- 一个不存在的地址
    ngx.var.backend = "http://127.0.0.1:1001"
    return
end

-- 如果sid不为空到8002
local sid = ngx.var.arg_sid

local cjson = require 'cjson'

if not sid then
    ngx.req.read_body()
    local data = ngx.req.get_body_data()
    if data then
        local params = cjson.decode(data)
        sid = params.sid
    end
end

if not sid then
    local user_agent = headers['User-Agent']
    if user_agent then
        if string.match(string.upper(user_agent), 'ANDROID') then
            ngx.var.backend = "http://127.0.0.1:8000"
        else
            ngx.var.backend = "http://127.0.0.1:8001"
        end
        ngx.log(ngx.ERR, 'user_agent: ' .. user_agent .. ' backend: ' .. ngx.var.backend)
        return
    end
else
    -- local l = string.len(sid)
    -- local last_char = string.byte(sid, l, l)
    -- if last_char % 2 == 0 then
    --     ngx.var.backend = "http://127.0.0.1:8000"
    --     ngx.log(ngx.ERR, 'sid: ' .. sid .. ' backend: ' .. ngx.var.backend)
    -- else
    --     ngx.var.backend = "http://127.0.0.1:8001"
    --     ngx.log(ngx.ERR, 'sid: ' .. sid .. ' backend: ' .. ngx.var.backend)
    -- end
    ngx.var.backend = "http://127.0.0.1:8002"
    ngx.log(ngx.ERR, 'sid: ' .. sid .. ' backend: ' .. ngx.var.backend)
end
