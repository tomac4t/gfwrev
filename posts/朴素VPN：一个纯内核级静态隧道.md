# 朴素VPN：一个纯内核级静态隧道

由于路由管控系统的建立，实时动态黑洞路由已成为最有效的封锁手段，TCP连接重置和DNS污染成为次要手段，利用漏洞的穿墙方法已不再具有普遍意义。对此应对方法是多样化协议的VPN来抵抗识别。这里介绍一种*太简单、有时很朴素*的“穷人VPN”。

朴素VPN只需要一次内核配置（Linux内核），即可永久稳定运行，不需要任何用户态守护进程。所有流量转换和加密全部由内核完成，原生性能，开销几乎没有。静态配置，避免动态握手和参数协商产生指纹特征导致被识别。并且支持NAT，移动的内网用户可以使用此方法。支持广泛，基于L2TPv3标准，Linux内核3.2\+都有支持，其他操作系统原则上也能支持。但有两个局限：需要root权限；一个隧道只支持一个用户。

朴素VPN利用UDP封装的静态L2TP隧道实现VPN，内核XFRM实现静态IPsec。实际上IP\-in\-IP隧道即可实现VPN，但是这种协议无法穿越NAT，因此必须利用UDP封装。内核3.18将支持[Foo\-over\-UDP](http://lwn.net/Articles/614348/)，在UDP里面直接封装IP，与静态的L2TP\-over\-UDP很类似。 
### 创建一个朴素VPN
**公共设置**
```bash
modprobe l2tp_eth
SERVER_IP=xxx.xxx.xxx.xxx SERVER_IF=eth0 CLIENT_IP=192.168.1.2 SESSION=0xdeadbeef COOKIE=baadc0defaceb00c
```
**服务器**
```bash
iptables -t nat -A INPUT -i $SERVER_IF -p udp --dport 5353 -m u32 --u32 '0>>22&0x3C@12 = 0xdeadbeef && 0>>22&0x3C@16 = 0xbaadc0de && 0>>22&0x3C@20 = 0xfaceb00c' -j SNAT --to-source 10.53.0.255:6464
ip l2tp add tunnel local $SERVER_IP remote 10.53.0.255 tunnel_id 1 peer_tunnel_id 1 encap udp udp_sport 5353 udp_dport 6464
ip l2tp add session tunnel_id 1 session_id $SESSION peer_session_id $SESSION cookie $COOKIE peer_cookie $COOKIE
ip addr add 10.53.0.1 peer 10.53.0.2 dev l2tpeth0
ip link set l2tpeth0 up mtu 1480
iptables -t nat -A POSTROUTING -o $SERVER_IF -s 10.53.0.2 -j MASQUERADE
sysctl -w net.ipv4.ip_forward=1
```
**客户端**
```bash
ip l2tp add tunnel local $CLIENT_IP remote $SERVER_IP tunnel_id 1 peer_tunnel_id 1 encap udp udp_sport 6464 udp_dport 5353
ip l2tp add session tunnel_id 1 session_id $SESSION peer_session_id $SESSION cookie $COOKIE peer_cookie $COOKIE
ip addr add 10.53.0.2 peer 10.53.0.1 dev l2tpeth0
ip link set l2tpeth0 up mtu 1480
ip route add 8.8.8.8 via 10.53.0.1
```


完成了！测试：（创建隧道后ARP启动也许会等几秒。）
```bash
user@client$ ping 10.53.0.1
PING 10.53.0.1 (10.53.0.1) 56(84) bytes of data.
64 bytes from 10.53.0.1: icmp_seq=1 ttl=64 time=154 ms
[...]
user@client$ dig twitter.com @8.8.8.8 +short
199.59.148.82
199.59.150.7
199.59.148.10
199.59.150.39
```

链路无污染！分步解释：

1. 端口5353、6464可自定义成比如端口53。服务器端口必须公网可访问，客户端可以在NAT内网里。服务端VPN内地址为`10.53.0.1`
，客户端为`.2`。`SESSION`和`COOKIE`一起组成一个32\+64位的密码。
2. 服务端验证这个密码然后设置SNAT。因此，同时只能有一个用户使用这个VPN。
3. 服务端创建静态L2TP隧道`l2tpeth0`
4. 服务端设置转发
5. 客户端创建静态L2TP隧道`l2tpeth0`
（NAT内网可）
6. 客户端设置路由（全局路由见下）

#### 安全性


关于协议识别，由于自定义的端口，静态的配置，没有任何动态的握手和参数协商过程，基于指纹的协议识别很难获得任何结果。（见下面附录的封包结构。）流量分析仍然有可能识别出某种特征，但是这种小众协议应该不容易成为目标。

关于加密，目前这个隧道未采用加密。我相信不太可能对任意端口的UDP都做深度检测。如果需要的话，可以看下面在隧道内进行IPsec加密的方法。

内核的L2TP隧道需要固定一个唯一的远程地址和端口，导致一个VPN只能有一个用户（多用户VPN的都是用户态实现的）。因此我们需要把NAT后的移动IP地址翻译回成固定地址和端口（`10.53.0.255:6464`）。为了防止拒绝服务，需要在SNAT的时候进行一个简易的认证，使用了L2TP的session id和cookie作为96位的密码。`conntrack -L -p udp`可以查看是哪个IP地址连接上了。如果用户的地址变了，要等到老SNAT连接记录超时注销（默认是三分钟）才能从新的地址连接，加速这个过程可以ssh登录然后`conntrack -D -p udp -s $OLD_CLIENT_IP`
清除老地址。Foo\-over\-UDP没有这96位的字段可以用来当作密码，所以认证需要使用另外的状态会略麻烦一些。

#### 客户端路由问题


可以设置全局VPN，如：
```bash
ip route add `ip route | sed -n "s/^default/$SERVER_IP/p"`
ip route add 0.0.0.0/1 via 10.53.0.1
ip route add 128.0.0.0/1 via 10.53.0.1
```

也可以使用chnroutes这类精细方案。

### 加密的朴素VPN（可选）


接着上面的设置，运行如下命令配置内核XFRM框架，实现一个朴素的静态IPsec隧道。

加密内网服务端地址为`10.53.1.1`，客户端为`.2`。安全关联参数`spi 102`及其静态密钥`0xc0de0102`和另外一组参数都可改。

1. 服务端创建加密隧道`ipsec0`

```bash
ip tunnel add ipsec0 mode ipip local 10.53.0.1 remote 10.53.0.2 dev l2tpeth0
ip addr add 10.53.1.1 peer 10.53.1.2 dev ipsec0
ip link set ipsec0 up
ip xfrm state add src 10.53.0.1 dst 10.53.0.2 proto esp spi 102 enc blowfish 0xc0de0102
ip xfrm state add src 10.53.0.2 dst 10.53.0.1 proto esp spi 201 enc blowfish 0xc0de0201
ip xfrm policy add dev l2tpeth0 dir out tmpl proto esp spi 102
ip xfrm policy add dev l2tpeth0 dir in tmpl proto esp spi 201
iptables -t nat -A POSTROUTING -o eth1 -s 10.53.1.2 -j MASQUERADE
```
2. 客户端创建加密隧道`ipsec0`

```bash
ip tunnel add ipsec0 mode ipip local 10.53.0.2 remote 10.53.0.1 dev l2tpeth0
ip addr add 10.53.1.2 peer 10.53.1.1 dev ipsec0
ip link set ipsec0 up
ip xfrm state add src 10.53.0.2 dst 10.53.0.1 proto esp spi 201 enc blowfish 0xc0de0201
ip xfrm state add src 10.53.0.1 dst 10.53.0.2 proto esp spi 102 enc blowfish 0xc0de0102
ip xfrm policy add dev l2tpeth0 dir out tmpl proto esp spi 201
ip xfrm policy add dev l2tpeth0 dir in tmpl proto esp spi 102
ip route del 8.8.8.8
ip route add 8.8.8.8 10.53.1.1
```

### 关闭VPN


如果没有设置IPsec，可以忽略`#ipsec`之后的命令。

1. 服务端
```bash
iptables -t nat -D INPUT -i eth1 -p udp --dport 5353 -m u32 --u32 '0>>22&0x3C@12 = 0xdeadbeef && 0>>22&0x3C@16 = 0xbaadc0de && 0>>22&0x3C@20 = 0xfaceb00c' -j SNAT --to-source $DUMMY_IP:6464
iptables -t nat -D POSTROUTING -o $SERVER_IF -s 10.53.0.2 -j MASQUERADE
#ipsec
ip xfrm state del src 10.53.0.1 dst 10.53.0.2 proto esp spi 102
ip xfrm state del src 10.53.0.2 dst 10.53.0.1 proto esp spi 201
ip xfrm policy del dev l2tpeth0 dir out
ip xfrm policy del dev l2tpeth0 dir in
iptables -t nat -D POSTROUTING -o $SERVER_IF -s 10.53.1.2 -j MASQUERADE
```
2. 客户端
```bash
ip route del $SERVER_IP
#ipsec
ip xfrm state del src 10.53.0.2 dst 10.53.0.1 proto esp spi 201
ip xfrm state del src 10.53.0.1 dst 10.53.0.2 proto esp spi 102
ip xfrm policy del dev l2tpeth0 dir out
ip xfrm policy del dev l2tpeth0 dir in
```
3. 公共
```bash
ip tunnel del ipsec0
ip l2tp del tunnel tunnel_id 1
```

### 附录


未加密的隧道客户端tcpdump监听`curl google.com`
能看到以下封包结构：
```bash
Internet Protocol Version 4, Src: 192.168.1.2, Dst: xxx.xxx.xxx.xxx
User Datagram Protocol, Src Port: 59126, Dst Port: 5353
Layer 2 Tunneling Protocol version 3
    Packet Type: Data    Message Session Id=0xdeadbeef
    Reserved: 0x0000
    Session ID: 0xdeadbeef
    Cookie: baadc0defaceb00c
Default L2-Specific Sublayer
Ethernet II, Src: xx:xx:xx:xx:xx:xx, Dst: xx:xx:xx:xx:xx:xx
Internet Protocol Version 4, Src: 10.53.0.2, Dst: 74.125.226.166 (google.com)
Transmission Control Protocol, Src Port: 39057, Dst Port: 80, Seq: 1, Ack: 1, Len: 74
Hypertext Transfer Protocol
```


Foo\-over\-UDP隧道与静态L2TP隧道非常类似，区别只是UDP里面没有封装L2TP包头和以太包头：
```bash
modprobe fou
# on the server
ip fou add port 5353 ipproto 4
iptables -t nat -A INPUT -i eth0 -p udp --dport 5353  -j SNAT --to-source 10.53.0.255:6464
ip link add udptun0 type ipip local $SERVER_IP remote 10.53.0.255 encap fou encap-sport 5353 encap-dport 6464
ip addr add 10.53.0.1 peer 10.53.0.2 dev udptun0
ip link set udptun0 up
[...]

# on the client
ip fou add port 6464 ipproto 4
ip link add udptun0 type ipip local $CLIENT_IP remote $SERVER_IP encap fou encap-sport 6464 encap-dport 5353
ip addr add 10.53.0.2 peer 10.53.0.1 dev udptun0
ip link set udptun0 up
[...]
```


转自：[https://gist.github.com/klzgrad/5661b64596d003f61980](https://gist.github.com/klzgrad/5661b64596d003f61980)