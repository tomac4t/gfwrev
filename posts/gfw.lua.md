```
-- gfw protocol
do
  ip_id_f = Field.new("ip.id");
  ip_df_f = Field.new("ip.flags.df");
  tcp_win_f = Field.new("tcp.window_size");
  gfw_proto = Proto("gfw", "GFW Postdissector")
  type_F = ProtoField.uint8("gfw.type", "Type")
  gfw_proto.fields = { type_F }
  function gfw_proto.dissector(buffer, pinfo, tree)
    local _ip_id = ip_id_f()
    local _tcp_win = tcp_win_f()
    local _ip_df = ip_df_f()
    local ip_id = tonumber(tostring(_ip_id))
    local tcp_win = tonumber(tostring(_tcp_win))
    local ip_df = tonumber(tostring(_ip_df))
    if (tcp_win ~= nil) and (ip_id ~= nil) and (ip_df ~= nil) then
      local type1, type2
      if (ip_id == 64) and (tcp_win % 17 == 0) and (ip_df == 0) then 
        type1 = true
      end
      local id = 65535 - tcp_win * 13;
      if id < 0 then id = id + 65536 end
      if (id == ip_id) and ip_df then
        type2 = true
      end
      if type1 or type2 then
        local subtree = tree:add(gfw_proto, "GFW Protocol Info")
        if type1 then subtree:add(type_F, 1)
        else subtree:add(type_F, 2) end
      end
    end
  end
  register_postdissector(gfw_proto)
end
```

![](../images/gfw_lua_1.png)

![](../images/gfw_lua_2.png)

![](../images/gfw_lua_3.png)

![](../images/gfw_lua_4.png)

-- 
[Google Docs -- Web word processing, presentations and spreadsheets.](http://docs.google.com/) [Edit this page (if you have permission)](http://docs.google.com/Doc?tab=edit&dr=true&id=dcg7wxzv_59n34swzv)

