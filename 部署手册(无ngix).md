# 验收文档生成器 — CentOS 离线部署手册（无 Nginx）

## 一、前置条件

- CentOS 7/8/Stream（x86_64）
- Python 3.12+（需预装）
- 约 200MB 磁盘空间

## 二、上传部署包

将 `docs_gen_deploy.tar.gz` 上传到服务器的 `/opt/` 目录：

```bash
mkdir -p /opt
cd /opt
tar -xzf docs_gen_deploy.tar.gz
cd docs_gen
```

## 三、安装 Python 依赖

```bash
cd /opt/docs_gen
pip install --no-index --find-links=./wheels -r requirements.txt
```

## 四、配置环境变量

```bash
# 复制并编辑配置文件
cp .env.example .env

# 生成随机密钥
python -c "import secrets; print(secrets.token_hex(32))"
# 将输出的密钥填入 .env 的 APP_SECRET_KEY=
```

编辑 `.env`，必须修改以下配置：

```ini
# JWT 签名密钥（必须改为随机字符串）
APP_SECRET_KEY=替换为上一步生成的密钥

# 默认 admin 初始密码（首次登录后修改）
ADMIN_DEFAULT_PASSWORD=admin123

# LLM 全局默认配置（用户也可在页面中配置自己的 LLM）
LLM_BASE_URL=http://your-llm-server:8000/v1
LLM_API_KEY=your-api-key-here
LLM_MODEL=your-model-name
```

其他配置有合理默认值，一般无需修改。完整配置说明见 `.env.example`。

## 五、创建 systemd 服务

```bash
cat > /etc/systemd/system/docs-gen.service << 'EOF'
[Unit]
Description=验收文档生成器
After=network.target

[Service]
Type=simple
User=root
WorkingDirectory=/opt/docs_gen
ExecStart=/usr/bin/python -m uvicorn backend.main:app --host 0.0.0.0 --port 80
Restart=always
RestartSec=5
Environment=PYTHONUNBUFFERED=1

[Install]
WantedBy=multi-user.target
EOF

systemctl daemon-reload
systemctl enable docs-gen
systemctl start docs-gen
```

> **说明**：FastAPI 直接监听 80 端口，同时提供 API 和前端页面（`main.py` 中已配置 `StaticFiles` 挂载 `frontend_dist/`），无需额外 Web 服务器。

## 六、防火墙配置

```bash
# 开放 80 端口
firewall-cmd --zone=public --add-port=80/tcp --permanent
firewall-cmd --reload
```

> 如果服务器未启用 firewalld，可能需要配置 iptables 或联系网络管理员开放端口。

## 七、验证部署

```bash
# 检查服务状态
systemctl status docs-gen

# 查看日志
journalctl -u docs-gen -f

# 测试接口
curl http://localhost:80/api/health
# 返回 {"status":"ok","version":"1.0.0"} 表示正常
```

浏览器访问 `http://服务器IP`，使用默认账号登录：

- 用户名：`admin`
- 密码：`admin123`（与 `.env` 中 `ADMIN_DEFAULT_PASSWORD` 一致）

## 八、首次登录后的操作

1. 在 **LLM 配置** 页面配置大模型连接信息（或使用全局默认配置）
2. 在 **文件管理** 页面上传参考文档（.docx/.pdf/.txt/.md/.xlsx）
3. 在 **文档生成** 页面选择模板、开始生成

## 九、目录结构

```
/opt/docs_gen/
├── backend/              # 后端源码
├── frontend_dist/        # 前端编译产物
├── wheels/               # Python 离线依赖包
├── storage/              # 运行时数据（自动创建）
│   ├── docs_gen.db       # SQLite 数据库
│   ├── uploads/          # 上传的参考文件
│   └── generated/        # 生成的 Word 文档
├── .env                  # 环境变量配置
├── .env.example          # 配置模板
└── requirements.txt      # Python 依赖清单
```

## 十、常用维护命令

```bash
# 启动
systemctl start docs-gen

# 停止
systemctl stop docs-gen

# 重启
systemctl restart docs-gen

# 查看实时日志
journalctl -u docs-gen -f

# 查看最近 100 条日志
journalctl -u docs-gen -n 100 --no-pager
```

## 十一、常见问题

**Q: 启动失败，提示端口被占用？**

```bash
# 查看 80 端口被谁占用
ss -tlnp | grep :80
# 修改 systemd 服务中 --port 80 为其他端口，如 --port 8080
# 然后 systemctl daemon-reload && systemctl restart docs-gen
# 记得同步修改防火墙规则
```

**Q: 页面能打开但 API 请求失败？**

检查防火墙是否开放了服务端口：
```bash
firewall-cmd --list-all
```

**Q: 文档生成失败？**

检查 LLM 配置是否正确，可在页面右上角 LLM 配置中点击"测试连接"。

**Q: 如何更新部署？**

```bash
systemctl stop docs-gen
# 替换 backend/ 和 frontend_dist/ 目录
# 如果有新依赖，更新 wheels/ 并重新安装
pip install --no-index --find-links=./wheels -r requirements.txt
systemctl start docs-gen
```

**Q: 如何备份数据？**

```bash
# 备份整个 storage 目录（包含数据库和文件）
cp -r /opt/docs_gen/storage /backup/docs_gen_storage_$(date +%Y%m%d)
```

**Q: 想用非 80 端口怎么办？**

修改 systemd 服务文件中的 `--port 80` 为其他端口（如 `--port 8080`），然后执行：
```bash
systemctl daemon-reload
systemctl restart docs-gen
```
别忘了同步修改防火墙规则。