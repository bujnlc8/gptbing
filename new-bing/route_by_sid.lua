local headers = ngx.req.get_headers()
-- 先判断referer
local referer = headers['Referer']
if referer and not string.match(referer, 'https://servicewechat.com/wxee7496be5b68b740') then
    ngx.log(ngx.ERR, 'referer: ' .. referer)
    -- 一个不存在的地址
    ngx.var.backend = 'http://127.0.0.1:1001'
    return
end

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
        -- Android分两个实例
        if string.match(string.upper(user_agent), 'ANDROID') then
            local remote_addr = ngx.var.remote_addr
            if remote_addr then
                local addr_sum = 0
                for word in string.gmatch(remote_addr, '[^\\.]+') do
                    addr_sum = addr_sum + tonumber(word)
                end
                -- local remote_addr_sub = string.gsub(remote_addr, '%.', '')
                -- remote_addr_sub = string.sub(remote_addr_sub, 3, 8)
                if addr_sum % 2 == 0 then
                    ngx.var.backend = 'http://127.0.0.1:8000'
                else
                    ngx.var.backend = 'http://127.0.0.1:8001'
                end
            else
                ngx.var.backend = 'http://127.0.0.1:8001'
            end
            ngx.log(ngx.ERR,
                'user_agent: ' .. user_agent .. ' backend: ' .. ngx.var.backend .. ' remote_addr: ' .. remote_addr)
        else
            ngx.var.backend = 'http://127.0.0.1:8002'
            ngx.log(ngx.ERR, 'user_agent: ' .. user_agent .. ' backend: ' .. ngx.var.backend)
        end
        return
    end
else
    ngx.var.backend = 'http://127.0.0.1:8003'
    ngx.log(ngx.ERR, 'sid: ' .. sid .. ' backend: ' .. ngx.var.backend)
end
