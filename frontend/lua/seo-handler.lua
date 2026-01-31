-- SEO Handler - Generates SEO-optimized HTML for bots from API
-- This script is executed by nginx/OpenResty when bot User-Agent is detected
-- It calls the backend API to fetch the profile instead of reading from filesystem

local cjson = require "cjson"

-- Utility: Escape HTML special characters
local function escape_html(str)
    if not str then return "" end
    return tostring(str):gsub("&", "&amp;")
                        :gsub("<", "&lt;")
                        :gsub(">", "&gt;")
                        :gsub('"', "&quot;")
                        :gsub("'", "&#39;")
end

-- Utility: Read file from filesystem
local function read_file(path)
    local file, err = io.open(path, "r")
    if not file then
        return nil, err
    end
    local content = file:read("*a")
    file:close()
    return content
end

-- Fetch profile from API via direct HTTP request
-- Using ngx.location.capture doesn't work reliably in content_by_lua context
-- Instead, use resty.http for direct HTTP call to backend
local http = require "resty.http"

-- Resolve backend address (same logic as /api/ location block)
local api_host = os.getenv("API_BACKEND_HOST") or ngx.var.api_host or "ai-resume-api"
local api_port = os.getenv("API_BACKEND_PORT") or ngx.var.api_port or "3000"
local target_ip = api_host

-- Handle IPv6
if api_host:find(":") then
    target_ip = api_host:find("%[") and api_host or "[" .. api_host .. "]"
end

local httpc = http.new()
httpc:set_timeout(5000)  -- 5 second timeout

local res, err = httpc:request_uri("http://" .. target_ip .. ":" .. api_port .. "/api/v1/profile", {
    method = "GET",
    headers = {
        ["Host"] = ngx.var.host,
    }
})

if not res then
    ngx.status = ngx.HTTP_INTERNAL_SERVER_ERROR
    ngx.header["Content-Type"] = "text/plain"
    ngx.say("Error: Failed to call profile API")
    ngx.log(ngx.ERR, "Profile API request failed: ", err)
    return ngx.exit(ngx.HTTP_INTERNAL_SERVER_ERROR)
end

if res.status ~= 200 then
    ngx.status = ngx.HTTP_INTERNAL_SERVER_ERROR
    ngx.header["Content-Type"] = "text/plain"
    ngx.say("Error: Profile API returned status " .. res.status)
    ngx.log(ngx.ERR, "Profile API returned status: ", res.status)
    return ngx.exit(ngx.HTTP_INTERNAL_SERVER_ERROR)
end

-- Parse JSON from API response
local ok, profile = pcall(cjson.decode, res.body)
if not ok then
    ngx.status = ngx.HTTP_INTERNAL_SERVER_ERROR
    ngx.header["Content-Type"] = "text/plain"
    ngx.say("Error: Invalid profile JSON from API")
    ngx.log(ngx.ERR, "Failed to parse profile API response: ", profile)
    ngx.log(ngx.ERR, "Response body: ", res.body)
    return ngx.exit(ngx.HTTP_INTERNAL_SERVER_ERROR)
end

-- Read SEO template
local template_path = "/etc/nginx/html/seo-template.html"

local template, err = read_file(template_path)

if not template then
    ngx.status = ngx.HTTP_INTERNAL_SERVER_ERROR
    ngx.header["Content-Type"] = "text/plain"
    ngx.say("Error: SEO template not found")
    ngx.log(ngx.ERR, "Failed to read seo-template.html: ", err)
    return ngx.exit(ngx.HTTP_INTERNAL_SERVER_ERROR)
end

ngx.log(ngx.INFO, "Template loaded, length: ", #template)

-- Extract first and last name from full name
local name_parts = {}
for part in string.gmatch(profile.name or "", "%S+") do
    table.insert(name_parts, part)
end
local first_name = name_parts[1] or ""
local last_name = table.concat(name_parts, " ", 2) or ""

-- Build tags string and tag badges HTML
local tags_string = ""
local tag_badges = ""
if profile.tags and type(profile.tags) == "table" then
    tags_string = table.concat(profile.tags, ", ")

    -- Generate badge HTML for first 10 tags
    for i, tag in ipairs(profile.tags) do
        if i > 10 then break end
        tag_badges = tag_badges .. '<span class="tag">' .. escape_html(tag) .. '</span>\n        '
    end
end

-- Construct domain dynamically from request
-- Check X-Forwarded-Proto header first (set by reverse proxy)
-- Fallback to ngx.var.scheme if behind reverse proxy that doesn't set it
local scheme = ngx.var.http_x_forwarded_proto or ngx.var.scheme or "https"
local domain = scheme .. "://" .. ngx.var.http_host

-- Set response headers BEFORE any output
ngx.header["Content-Type"] = "text/html; charset=utf-8"
ngx.header["Cache-Control"] = "public, max-age=3600" -- Cache for 1 hour

-- Replace all placeholders in template
local html = template

local substitutions = {
    ["{{NAME}}"] = escape_html(profile.name or ""),
    ["{{TITLE}}"] = escape_html(profile.title or ""),
    ["{{EMAIL}}"] = escape_html(profile.email or ""),
    ["{{LINKEDIN}}"] = escape_html(profile.linkedin or ""),
    ["{{LOCATION}}"] = escape_html(profile.location or ""),
    ["{{STATUS}}"] = escape_html(profile.status or ""),
    ["{{TAGS}}"] = escape_html(tags_string),
    ["{{FIRST_NAME}}"] = escape_html(first_name),
    ["{{LAST_NAME}}"] = escape_html(last_name),
    ["{{DOMAIN}}"] = escape_html(domain),
    ["{{TAG_BADGES}}"] = tag_badges
}

for pattern, replacement in pairs(substitutions) do
    html = html:gsub(pattern, replacement)
end

-- Log successful render
ngx.log(ngx.INFO, "SEO page rendered for bot: ", ngx.var.http_user_agent, " (", #html, " bytes)")

-- Return HTML
ngx.say(html)
