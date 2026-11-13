<p align="center"><img src="assets/covers/25-xiaozhi-kit.jpg" alt="小智套件 项目封面" width="100%"></p>

<h1 align="center">Xiaozhi Kit · 小智开发套件</h1>

<p align="center">ESP32 小智音箱的开源工具链：命令行、Web 控制台与 Cursor Skill</p>

<p align="center">
  <a href="LICENSE">MIT 许可</a>
</p>

## 简介

替代市面上封闭的串口 GUI：一套命令行把固件烧写、串口调试、配网走完，另带本地 Web 控制台和给 AI 编程工具用的 Skill 定义，便于接入自动化。

## 功能

- **AI 友好 CLI**：`xzkit` 一条命令完成设备发现、烧写、日志
- **本地 Web 控制台**：浏览器管理设备，不必装桌面客户端
- **Cursor Skill**：给 AI 编程工具的项目上下文定义，直接对话改固件
- **可脚本化**：输出结构化结果，方便接进 CI 或批量刷机流程

## 安装

```bash
pip install xzkit      # 或从源码安装
xzkit --help
```

## 目录

```
cli/          命令行入口
web/          Web 控制台
skill/        Cursor Skill 定义
docs/         使用文档
```

## 许可证

[MIT](LICENSE)
