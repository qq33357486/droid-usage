# Droid 用量查询

一个用于查询 [Factory AI Droid](https://factory.ai) API Key 用量的 Web 工具。

## 功能

- 添加多个 API Key 进行管理
- 查看每个 Key 的初始额度、剩余额度、余额百分比
- 一键刷新所有 Key 的用量
- 一键清理余额低于 5% 的 Key
- 暗色主题，护眼舒适

## 隐私说明

**API Key 仅存储在你的浏览器本地 (localStorage)，服务器不存储任何 Key 信息。**

服务器仅作为代理转发请求到 Factory AI API，解决浏览器跨域限制问题。

## 快速部署

### Docker Compose (推荐)

```bash
curl -O https://raw.githubusercontent.com/qq33357486/droid-usage/master/docker-compose.yml
docker-compose up -d
```

### Docker

```bash
docker run -d -p 8003:8003 --restart always --name droid-usage qq33357486/droid-usage:latest
```

### 本地运行

```bash
git clone https://github.com/qq33357486/droid-usage.git
cd droid-usage
python server.py
```

## 使用方法

1. 部署后访问 `http://服务器IP:8003`
2. 输入你的 Droid API Key 并点击添加
3. 系统自动查询并显示用量信息
4. 点击「刷新全部」更新所有 Key 的用量
5. 点击「清理快用完的」删除余额低于 5% 的 Key

## 安全建议

**生产环境部署时，强烈建议使用 HTTPS 来保护 API Key 传输安全。**

推荐使用 Nginx 或 Caddy 作为反向代理并配置 SSL：

### Nginx 配置示例

```nginx
server {
    listen 443 ssl;
    server_name your-domain.com;
    
    ssl_certificate /path/to/cert.pem;
    ssl_certificate_key /path/to/key.pem;
    
    location / {
        proxy_pass http://127.0.0.1:8003;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }
}
```

### Caddy 配置示例

```
your-domain.com {
    reverse_proxy localhost:8003
}
```

Caddy 会自动申请和续期 Let's Encrypt 证书。

## License

MIT
