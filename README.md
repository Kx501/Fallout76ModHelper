# Fallout76 Mod 助手

一个用于管理 Fallout 76 Mod 的 Python 工具，提供 Mod 安装、更新检查、配置管理等功能。

## 功能特性

### 核心功能

- **安装 Mod**：支持批量安装 ZIP、7Z、RAR 格式的 Mod 压缩包
- **查看 Mod 列表**：显示所有已注册的 Mod，包括启用/未启用状态、版本信息等
- **检查 Mod 更新**：通过 Nexus Mods API 检查已安装 Mod 的更新（需要配置 API Key）
- **更新 Mod 信息**：自动检测并更新 Mod 的版本号和 Nexus Mod ID
- **Mod 排序**：可视化调整 Mod 加载顺序
- **更新 INI 配置**：自动同步 Mod 到 `Fallout76Custom.ini` 文件
- **删除 Mod**：一键删除 Mod（包括文件、配置、注册信息）
- **打开目录**：快速打开游戏目录或配置目录
- **启动游戏**：通过 Steam 启动游戏

### 高级特性

- **文件排除规则**：类似 `.gitignore` 的排除机制，可在安装时自动过滤不需要的文件（如图片、文本文件等）
- **自动备份**：安装 Mod 前自动备份配置文件（.ini、.json）
- **特殊 Mod 支持**：支持特殊安装路径的 Mod（如 SFE）
- **Mod 注册信息**：记录 Mod 的版本、安装时间、来源等信息
- **安装方式选择**：支持直接移动（direct）或复制（copy）两种安装方式

## 安装要求

### Python 版本

- Python 3.7+

### 依赖库

```bash
pip install -r requirements.txt
```

主要依赖：

- `py7zr`（可选，用于解压 7Z 文件）
- `rarfile`（可选，用于解压 RAR 文件）

## 配置说明

首次运行会在 `configs/config.json` 创建默认配置文件，主要配置项：

```json
{
  "game_path": null,                    // 游戏安装路径（自动检测）
  "launch_url": "steam://rungameid/1151340",
  "ini_mode": "sResourceArchive2List",  // INI 配置模式
  "backup_extensions": [".json", ".ini"], // 需要备份的文件扩展名
  "ini_backup_retention": 5,            // 保留的备份数量
  "mod_archive_directory": null,        // 默认 Mod 压缩包目录
  "default_install_method": "direct",   // 默认安装方式：direct/copy
  "exclude_patterns": [                  // 文件排除规则（类似 .gitignore）
    "*.png",
    "*.jpg",
    "*.txt"
  ],
  "nexus_api": {
    "api_key": ""                       // Nexus Mods API Key（用于检查更新）
  },
  "special_mod_install_paths": {        // 特殊 Mod 安装路径
    "SFE": "."
  }
}
```

### 文件排除规则

`exclude_patterns` 支持通配符匹配，例如：

- `*.png` - 排除所有 PNG 图片
- `*.txt` - 排除所有文本文件
- `specific.xml` - 排除特定文件名的 XML 文件

被排除的文件仍会解压到 `mods/` 文件夹，但不会安装到游戏的 Data 目录。

### Mod 注册信息文件

程序会在 `configs/mods_registry.json` 中记录所有已安装 Mod 的详细信息：

```json
{
  "mods": {
    "HUDChallenges.ba2": {
      "name": "HUDChallenges.ba2",              // Mod 文件名
      "alias": null,                            // Mod 显示别名（可手动设置）
      "version": "1.2.4",                       // Mod 版本号
      "nexus_mod_id": "2860",                   // Nexus Mods 的 Mod ID（用于检查更新）
      "enabled": true,                          // 是否已启用（在 INI 配置中）
      "order": 1,                               // Mod 加载顺序（数字越小越先加载）
      "install_method": "copy",                 // 安装方式：direct/copy
      "source_file": "HUDChallenges-2860-1-2-4-1761234069.zip",  // 原始压缩包文件名
      "install_date": "2025-11-01T14:14:09.972557"  // 安装时间（ISO 格式）
    }
  }
}
```

## 使用方法

### 启动程序

```bash
python main.py
```

或运行

```bash
main.exe
```

### 菜单选项

1. **启动游戏** - 通过 Steam 启动 Fallout 76
2. **安装 Mod** - 批量安装 Mod 压缩包
3. **查看 Mod 列表** - 查看所有已注册的 Mod 及其状态
4. **检查 Mod 更新** - 检查已安装 Mod 是否有更新（需要 Nexus API Key）
5. **更新 Mod 信息** - 从 `mods/` 目录检测并更新 Mod 信息
6. **更新 Mod 排序** - 调整 Mod 加载顺序
7. **更新 Fallout76Custom.ini** - 同步 Mod 配置到 INI 文件
8. **删除 Mod** - 删除选定的 Mod（支持多选）
9. **打开目录** - 打开游戏目录或配置目录

## 目录结构

```
FalloutHelper/
├── main.py                 # 主程序入口
├── mod_installer.py        # Mod 安装模块
├── mod_registry.py         # Mod 注册信息管理
├── ini_manager.py          # INI 配置文件管理
├── path_detector.py        # 路径自动检测
├── game_launcher.py        # 游戏启动器
├── nexus_api.py           # Nexus Mods API 客户端
├── logger.py               # 日志模块
├── configs/                # 配置目录
│   ├── config.json        # 主配置文件
│   └── mods_registry.json # Mod 注册信息
├── mods/                  # Mod 解压目录
├── backups/               # 备份目录
└── logs/                  # 日志目录
```

## 注意事项

1. **首次使用**：程序会自动检测游戏路径和配置目录，如果检测失败需要手动在配置文件中设置
2. **Nexus API Key**：检查 Mod 更新功能需要配置 Nexus Mods API Key，可在 [Nexus Mods](https://next.nexusmods.com/settings/api-keys) 获取
3. **备份机制**：安装 Mod 前会自动备份 `.ini` 和 `.json` 配置文件，保留最近 5 个备份
4. **Mod 排序**：Mod 的加载顺序会影响游戏中的效果，建议按照 Mod 说明调整顺序

## 许可证

本项目仅供学习和个人使用。

## 致谢

本项目使用了以下优秀的工具和库：

- **[Nuitka](https://nuitka.net/)**
- **[UnRAR](https://www.rarlab.com/rar_add.htm)**
- **[py7zr](https://github.com/miurahr/py7zr)**
- **[rarfile](https://github.com/markokr/rarfile)**

感谢这些项目的开发者和贡献者！

## 贡献

欢迎提交 Issue 和 Pull Request！
