"""
Fallout76 Mod 安装脚本 - 主入口
"""
import os
import sys
import json
from path_detector import PathDetector
from logger import get_logger
from ini_manager import IniManager
from mod_installer import ModInstaller
from game_launcher import GameLauncher
from mod_registry import ModRegistry
from nexus_api import NexusAPI

logger = get_logger()

# TODO: 使用按键选择的菜单

def load_config():
    """加载配置文件，如果不存在则创建默认配置"""
    # 获取脚本所在目录
    script_dir = os.path.dirname(os.path.abspath(__file__))
    config_dir = os.path.join(script_dir, 'configs')
    config_path = os.path.join(config_dir, 'config.json')
    
    # 确保 configs 目录存在
    os.makedirs(config_dir, exist_ok=True)
    
    # 如果配置文件不存在，创建默认配置
    if not os.path.exists(config_path):
        default_config = {
            "game_path": None,
            "launch_url": "steam://rungameid/1151340",
            "mod_archive_directory": None,
            "ini_mode": "sResourceArchive2List",
            "ini_backup_retention": 0,
            "backup_extensions": [".json", ".ini"],
            "nexus_api": {
                "api_key": ""
            },
            "default_install_method": "direct",
            "exclude_patterns": [
                "*.png",
                "*.jpg",
                "*.jpeg",
                "*.txt",
                "*.md",
                "__HowToInstall_visual.html"
            ],
            "special_mod_install_paths": {
                "SFE": "."
            }
        }
        try:
            with open(config_path, 'w', encoding='utf-8') as f:
                json.dump(default_config, f, indent=2, ensure_ascii=False)
            logger.info(f"创建默认配置文件: {config_path}")
        except Exception as e:
            logger.error(f"创建默认配置文件失败: {e}")
            return {}
    
    # 加载配置文件
    try:
        with open(config_path, 'r', encoding='utf-8') as f:
            return json.load(f)
    except Exception as e:
        logger.error(f"加载配置文件失败: {e}")
        return {}


def display_menu():
    """显示主菜单"""
    print("\n" + "=" * 50)
    print("Fallout76 Mod 助手")
    print("=" * 50)
    print("1. 启动游戏")
    print("2. 安装 Mod")
    print("3. 查看 Mod 列表")
    print("4. 检查 Mod 更新")
    print("5. 更新 Mod 信息")
    print("6. 更新 Mod 排序")
    print("7. 更新 Fallout76Custom.ini")
    print("8. 删除 Mod")
    print("9. 打开目录")
    print("0. 退出")
    print("=" * 50)


def launch_game():
    """启动游戏"""
    logger.info("准备启动游戏...\n")
    
    # 初始化路径检测器
    path_detector = PathDetector()
    paths = path_detector.get_all_paths()
    
    if not paths['game_path']:
        logger.error("未找到游戏路径，请检查 configs/config.json 配置")
        return
    
    # 初始化游戏启动器
    launcher = GameLauncher()
    launcher.set_game_path(paths['game_path'])
    
    logger.info("=" * 50)
    logger.info("开始启动游戏")
    
    success = launcher.launch()
    if success:
        logger.info("游戏启动成功")
    else:
        logger.error("游戏启动失败")
    
    logger.info("=" * 50)


def install_mods():
    """安装 Mod"""
    logger.info("准备安装 Mod...\n")
    
    # 初始化路径检测器
    path_detector = PathDetector()
    paths = path_detector.get_all_paths()
    
    if not paths['data_path']:
        logger.error("未找到游戏 Data 目录")
        return
    
    if not paths['config_dir']:
        logger.error("未找到配置目录")
        return
    
    # 加载配置
    config = load_config()
    mod_archive_directory = config.get('mod_archive_directory')
    
    # 获取 mod 文件夹路径
    mod_folder = None
    if mod_archive_directory:
        # 展开环境变量并检查路径
        expanded_path = os.path.expandvars(mod_archive_directory)
        if os.path.exists(expanded_path) and os.path.isdir(expanded_path):
            mod_folder = expanded_path
            logger.info(f"使用默认 Mod 目录: {mod_folder}")
        else:
            logger.warning(f"配置的默认 Mod 目录不存在: {expanded_path}")
    
    if not mod_folder:
        print("\n请输入 Mod 文件夹路径（包含 ZIP 压缩包的文件夹）:")
        mod_folder = input("> ").strip().strip('"').strip("'")
        print("")
        if not mod_folder:
            logger.error("路径不能为空")
            return
        # 展开环境变量
        mod_folder = os.path.expandvars(mod_folder)
    
    if not os.path.exists(mod_folder):
        logger.error(f"路径不存在: {mod_folder}")
        return
    
    if not os.path.isdir(mod_folder):
        logger.error(f"不是文件夹: {mod_folder}")
        return
    
    # 获取其他配置（已在上面加载过，这里直接使用）
    backup_extensions = config.get('backup_extensions', ['.json', '.ini'])
    backup_retention = config.get('ini_backup_retention', 0)
    
    # 初始化 Mod 注册信息
    mod_registry = ModRegistry()
    
    # 初始化 INI 管理器
    ini_manager = IniManager(paths['config_dir'], backup_retention=backup_retention)
    
    # 初始化 Mod 安装器
    installer = ModInstaller(
        paths['data_path'],
        paths['config_dir'],
        ini_manager,
        mod_registry=mod_registry,
        backup_extensions=backup_extensions,
        game_path=paths.get('game_path')
    )
    
    logger.info(f"开始安装 Mod，从文件夹: {mod_folder}")
    logger.info("=" * 50)
    
    # 扫描文件夹，获取所有压缩包文件（完整路径）
    archive_files = []
    archive_names = []
    for item in os.listdir(mod_folder):
        item_path = os.path.join(mod_folder, item)
        item_lower = item.lower()
        if os.path.isfile(item_path) and (item_lower.endswith('.zip') or item_lower.endswith('.7z') or item_lower.endswith('.rar')):
            archive_files.append(item_path)  # 完整路径，用于安装
            archive_names.append(item)  # 文件名，用于显示和用户选择
    
    if not archive_files:
        logger.info("=" * 50)
        logger.warning("未找到压缩包文件")
        return
    
    # 显示找到的模组列表
    logger.info(f"找到 {len(archive_files)} 个压缩包文件:")
    for idx, archive_name in enumerate(archive_names, 1):
        logger.info(f"  {idx}. {archive_name}")
    
    logger.info("=" * 50)
    
    # 安装方式选择
    default_method = config.get('default_install_method', 'direct')
    logger.info(f"默认安装方式: {default_method} (direct=直接移动, copy=复制)\n")
    logger.info("提示: 可在 Mod 注册信息中手动修改安装方式，修改将在下次安装时生效")
    print("\n是否手动选择安装方式? (y/N): ", end='')
    print("")
    manual_choice = input().strip().lower()
    
    user_choices = {}
    if manual_choice == 'y':
        # 手动选择每个模组的安装方式
        logger.info("开始逐个选择安装方式...")
        for archive_name in archive_names:
            display_name = mod_registry.extract_mod_name_from_filename(archive_name) if mod_registry else archive_name
            print(f"\n[{display_name}] 的安装方式:")
            print("  1. 移动文件 (direct)")
            print("  2. 复制文件 (copy)")
            print(f"  默认: {default_method} (按 Enter)")
            choice = input("\n请选择: ").strip()
            
            if choice == '1':
                user_choices[archive_name] = 'direct'
            elif choice == '2':
                user_choices[archive_name] = 'copy'
            # 如果选择为空或其他值，使用默认（不添加到user_choices中）
    else:
        logger.info("使用默认安装方式")
    
    logger.info("=" * 50)
    result = installer.install_mods_from_folder(mod_folder, user_choices=user_choices, archive_files=archive_files)
    
    logger.info("=" * 50)
    logger.info(f"安装完成!")
    logger.info(f"成功: {result['success']} 个")
    logger.info(f"失败: {result['failed']} 个")
    
    if result['mods']:
        logger.info(f"已添加到 INI 配置的 Mod 文件:")
        for idx, mod_file in enumerate(result['mods'], 1):
            logger.info(f"  {idx}. {mod_file}")


def view_mod_list():
    """查看 Mod 列表（包括启用和未启用的）"""
    logger.info("查询 Mod 列表...\n")
    
    # 初始化 Mod 注册信息
    mod_registry = ModRegistry()
    
    # 获取所有 mod（按 order 排序）
    sorted_mods = mod_registry.get_mods_by_order(enabled_only=False)
    
    if not sorted_mods:
        logger.info("当前没有已注册的 Mod\n")
        return
    
    # 分离启用和未启用的 mod
    enabled_mods = []
    disabled_mods = []
    for mod_name, mod_info in sorted_mods:
        if mod_info.get('enabled', False):
            enabled_mods.append(mod_name)
        else:
            disabled_mods.append(mod_name)
    
    total_count = len(sorted_mods)
    enabled_count = len(enabled_mods)
    disabled_count = len(disabled_mods)
    
    # 加载配置以获取 INI 模式
    config = load_config()
    ini_mode = config.get('ini_mode', 'sResourceArchive2List')
    
    # 初始化路径检测器和 INI 管理器以获取当前 INI 中的 mod
    path_detector = PathDetector()
    paths = path_detector.get_all_paths()

    logger.info(f"Mod 列表 (共 {total_count} 个, 启用: {enabled_count} 个, 未启用: {disabled_count} 个):")
    logger.info("=" * 50)
    
    if paths['config_dir']:
        backup_retention = config.get('ini_backup_retention', 0)
        ini_manager = IniManager(paths['config_dir'], backup_retention=backup_retention)
        current_ini_mods = ini_manager.get_mod_list(ini_mode)
    else:
        current_ini_mods = []
    
    # 显示所有 mod 信息（按 order 排序）
    idx = 1
    for mod_name, mod_info in sorted_mods:
        # 检查启用状态
        is_enabled = mod_info.get('enabled', False)
        
        # 检查是否在 INI 中
        in_ini = mod_name in current_ini_mods
        
        # 确定状态
        if is_enabled:
            if in_ini:
                status = "✓ 已启用"
            else:
                status = "⚠ 已启用但配置丢失"
        else:
            status = "✗ 未启用"
        
        # 使用显示名称（别名或原始名称）
        display_name = mod_registry.get_display_name(mod_name)
        
        logger.info(f"{idx}. {display_name}")
        logger.info(f"   状态: {status}")
        
        if mod_info:
            if mod_info.get('version'):
                logger.info(f"   版本: {mod_info['version']}")
            if mod_info.get('install_date'):
                from datetime import datetime
                try:
                    install_date = datetime.fromisoformat(mod_info['install_date'])
                    logger.info(f"   安装时间: {install_date.strftime('%Y-%m-%d %H:%M:%S')}")
                except:
                    logger.info(f"   安装时间: {mod_info['install_date']}")
            if mod_info.get('source_file'):
                logger.info(f"   来源文件: {mod_info['source_file']}")
        
        idx += 1
    
    logger.info("=" * 50)
    logger.info("Mod 列表查询完成\n")
    
    # 紧凑显示启用和未启用的mod列表
    if enabled_mods:
        enabled_display_names = [mod_registry.get_display_name(mod_name) for mod_name in enabled_mods]
        logger.info(f"已启用 ({enabled_count}):")
        logger.info(f"{', '.join(enabled_display_names)}")
        print("")
    if disabled_mods:
        disabled_display_names = [mod_registry.get_display_name(mod_name) for mod_name in disabled_mods]
        logger.info(f"未启用 ({disabled_count}):")
        logger.info(f"{', '.join(disabled_display_names)}")
        print("")
    
    # 检查是否有丢失的配置
    if current_ini_mods:
        missing_mods = [mod for mod in enabled_mods if mod not in current_ini_mods]
        if missing_mods:
            logger.warning(f"发现 {len(missing_mods)} 个已启用的 Mod 配置丢失:")
            logger.info("=" * 50)
            for idx, mod_name in enumerate(missing_mods, 1):
                mod_info = mod_registry.get_mod_info(mod_name)
                version = mod_info.get('version', '未知') if mod_info else '未知'
                display_name = mod_registry.get_display_name(mod_name)
                logger.info(f"{idx}. {display_name} (版本: {version})")
            logger.info("=" * 50)
            
            print("\n是否恢复这些 Mod 的配置? (Y/n): ", end='')
            restore = input().strip()
            
            if restore and restore.lower() != 'y':
                logger.info("已取消恢复操作\n")
                return
            
            logger.info(f"开始恢复 {len(missing_mods)} 个丢失的 Mod 配置")
            logger.info("=" * 50)
            
            restored_count = 0
            failed_count = 0
            
            with ini_manager:
                for mod_name in missing_mods:
                    # 检查 mod 是否在注册信息中
                    mod_info = mod_registry.get_mod_info(mod_name)
                    if not mod_info:
                        logger.warning(f"{mod_name} 不在注册信息中，跳过")
                        failed_count += 1
                        continue
                    
                    # 添加 mod 到 INI 配置
                    if ini_manager.add_mod_to_list(mod_name, ini_mode):
                        mod_registry.mark_mod_enabled(mod_name)
                        restored_count += 1
                        logger.info(f"成功恢复 {mod_name} 的配置")
                    else:
                        logger.error(f"恢复 {mod_name} 的配置失败")
                        failed_count += 1
            
            logger.info("=" * 50)
            logger.info(f"恢复完成: 成功 {restored_count} 个, 失败 {failed_count} 个\n")




def check_mod_updates():
    """检查 Mod 更新"""
    logger.info("开始检查 Mod 更新...\n")
    
    # 加载配置
    config = load_config()
    api_config = config.get('nexus_api', {})
    api_key = api_config.get('api_key', '').strip()
    
    if not api_key:
        logger.warning("未配置 Nexus Mods API Key")
        logger.warning("请在 configs/config.json 中配置 nexus_api.api_key")
        return
    
    # 初始化 Nexus API 客户端
    try:
        nexus_api = NexusAPI(api_key)
        logger.info("Nexus API 客户端初始化成功")
    except Exception as e:
        logger.error(f"初始化 Nexus API 失败: {e}")
        return
    
    # 初始化 Mod 注册信息
    mod_registry = ModRegistry()
    
    # 获取所有已启用的 mod（或所有有 nexus_mod_id 的 mod）
    all_mods = mod_registry.list_mods()
    mods_with_id = [mod for mod in all_mods if mod.get('nexus_mod_id')]
    
    if not mods_with_id:
        logger.info("当前没有包含 Nexus Mod ID 的 Mod\n")
        return
    
    logger.info(f"正在检查 {len(mods_with_id)} 个 Mod 的更新...")
    logger.info("=" * 50)
    
    updated_mods = []
    no_update_mods = []
    error_mods = []
    
    for mod_info in mods_with_id:
        mod_name = mod_info['name']
        mod_id = mod_info.get('nexus_mod_id')
        current_version = mod_info.get('version')
        source_file = mod_info.get('source_file')
        
        if not mod_id:
            continue
        
        # 使用显示名称（别名或原始名称）
        display_name = mod_registry.get_display_name(mod_name)
        
        # logger.info(f"检查更新: {display_name}")
        logger.info(f"Mod ID: {mod_id}, {display_name}")
        
        # 从 source_file 提取模组名（使用更精确的提取方法）
        mod_name_prefix = mod_registry.extract_mod_name_from_filename(source_file) if source_file else None
        
        # 获取最新版本信息
        latest_info = nexus_api.get_latest_version(mod_id, mod_name=mod_name_prefix)
        
        if not latest_info:
            error_mods.append((display_name, "无法获取更新信息"))
            logger.warning(f"{display_name}: 无法获取更新信息")
            continue
        
        # 检查是否找到匹配的文件
        matched = latest_info.get('matched', True)
        if not matched:
            logger.warning(f"{display_name}: 未找到匹配的文件名，需要自行前往网页确认")
        
        latest_version = latest_info.get('version')
        
        # 如果找不到匹配的文件，不进行版本比较
        if not matched:
            # 仍然添加到 updated_mods 中，但标记为需要手动确认
            updated_mods.append((display_name, current_version, "未知", latest_info))
            continue
        
        if not latest_version:
            error_mods.append((display_name, "无法识别版本号"))
            logger.warning("无法识别版本号")
            continue
        
        # 比较版本
        if not current_version:
            # 如果没有当前版本号，假设有更新
            updated_mods.append((display_name, current_version, latest_version, latest_info))
            logger.info(f"发现新版本 {latest_version}")
        else:
            has_update = nexus_api.compare_versions(current_version, latest_version)
            if has_update:
                updated_mods.append((display_name, current_version, latest_version, latest_info))
                logger.info(f"发现新版本 {current_version} -> {latest_version}")
            elif has_update is False:
                no_update_mods.append((display_name, current_version, latest_version))
                logger.info(f"已是最新版本 ({current_version})")
            else:
                # 无法比较版本（格式不同等）
                if current_version != latest_version:
                    # 版本号字符串不同，可能是有更新
                    updated_mods.append((display_name, current_version, latest_version, latest_info))
                    logger.info(f"版本号不同（无法比较） {current_version} -> {latest_version}")
                else:
                    no_update_mods.append((display_name, current_version, latest_version))
                    logger.info(f"已是最新版本 ({current_version})")
    
    logger.info("=" * 50)
    logger.info(f"检查完成: 发现 {len(updated_mods)} 个更新")
    logger.info(f"已是最新: {len(no_update_mods)} 个, 错误: {len(error_mods)} 个")
    
    if updated_mods:
        logger.info("可更新 Mod:")
        for display_name, old_version, new_version, latest_info in updated_mods:
            mod_url = latest_info.get('mod_url', '')
            logger.info(f"• {display_name}: {old_version or '未知'} -> {new_version}")
            if mod_url:
                logger.info(f"|__{mod_url}")
    else:
        logger.info(f"所有 Mod 都已是最新版本\n")
    
    if error_mods:
        logger.warning(f"{len(error_mods)} 个 Mod 检查失败:")
        for mod_name, error_msg in error_mods:
            logger.warning(f"• {mod_name}: {error_msg}")


def detect_mod_info():
    """检测 Mod 信息并更新注册信息"""
    logger.info("开始检测 Mod 信息...\n")
    
    # 获取脚本目录下的 mods/ 文件夹
    script_dir = os.path.dirname(os.path.abspath(__file__))
    mods_dir = os.path.join(script_dir, 'mods')
    
    if not os.path.exists(mods_dir) or not os.path.isdir(mods_dir):
        logger.error("mods/ 目录不存在")
        return
    
    # 初始化 Mod 注册信息
    mod_registry = ModRegistry()
    
    # 获取 mods/ 目录下的所有子文件夹
    mod_folders = []
    for item in os.listdir(mods_dir):
        item_path = os.path.join(mods_dir, item)
        if os.path.isdir(item_path):
            mod_folders.append((item, item_path))
    
    if not mod_folders:
        logger.info("mods/ 目录下没有 Mod 子文件夹\n")
        return
    
    logger.info(f"检测到 {len(mod_folders)} 个 Mod 文件夹")
    logger.info("=" * 50)
    
    updated_count = 0
    new_count = 0
    
    for folder_name, folder_path in mod_folders:
        # 从文件夹名称提取信息（文件夹名通常是 ZIP 文件名去掉扩展名）
        # 尝试从文件夹名提取版本号和 Mod ID（将文件夹名作为文件名处理）
        version = mod_registry._extract_version_from_filename(folder_name)
        nexus_mod_id = mod_registry._extract_nexus_mod_id_from_filename(folder_name)
        
        # 在文件夹中查找 mod 文件（.ba2, .esm, .esp）
        mod_files = []
        for file_item in os.listdir(folder_path):
            file_path = os.path.join(folder_path, file_item)
            if os.path.isfile(file_path):
                ext = os.path.splitext(file_item)[1].lower()
                if ext in ['.ba2', '.esm', '.esp']:
                    mod_files.append(file_item)
        
        if not mod_files:
            logger.debug(f"文件夹 {folder_name} 中没有找到 mod 文件")
            continue
        
        # 为每个 mod 文件更新信息
        for mod_file in mod_files:
            mod_info = mod_registry.get_mod_info(mod_file)
            
            if mod_info:
                # 更新已存在的 mod 信息
                old_version = mod_info.get('version')
                old_mod_id = mod_info.get('nexus_mod_id')
                
                has_update = False
                update_parts = []
                
                # 更新版本号
                if version and version != old_version:
                    mod_registry.update_mod_version(mod_file, version)
                    update_parts.append(f"版本号: {version}")
                    has_update = True
                
                # 更新 Nexus Mod ID
                if nexus_mod_id and str(nexus_mod_id) != str(old_mod_id):
                    mod_info['nexus_mod_id'] = nexus_mod_id
                    mod_registry.mods[mod_file] = mod_info
                    mod_registry._save_registry()
                    update_parts.append(f"Mod ID: {nexus_mod_id}")
                    has_update = True
                
                if has_update:
                    updated_count += 1
                    logger.info(f"更新信息 {mod_file}")
                    for part in update_parts:
                        logger.info(f"  {part}")
            else:
                # 新发现的 mod（不在注册信息中）
                # 如果有版本号或 Mod ID 信息，注册它
                # 注意：这里传入 None 而不是 folder_path，因为 register_mod 期望压缩包文件路径
                # 而 detect_mod_info 处理的是已解压的文件夹，版本和 mod_id 已从文件夹名中提取
                if version or nexus_mod_id:
                    mod_registry.register_mod(mod_file, None, version, nexus_mod_id, enabled=False)
                    new_count += 1
                    logger.info(f"新发现 mod: {mod_file}")
                    if version:
                        logger.info(f"  版本号: {version}")
                    if nexus_mod_id:
                        logger.info(f"  Mod ID: {nexus_mod_id}")
                    
    logger.info("=" * 50)
    logger.info(f"Mod 信息检测完成")
    logger.info(f"更新: {updated_count} 个, 新发现: {new_count} 个")


def reorder_mods():
    """Mod 排序功能"""
    logger.info("开始 Mod 排序功能...\n")
    logger.info("=" * 50)
    
    # 初始化路径检测器
    path_detector = PathDetector()
    paths = path_detector.get_all_paths()
    
    if not paths['config_dir']:
        logger.error("未找到配置目录")
        logger.info("=" * 50)
        return
    
    # 加载配置
    config = load_config()
    ini_mode = config.get('ini_mode', 'sResourceArchive2List')
    backup_retention = config.get('ini_backup_retention', 0)
    
    # 初始化 Mod 注册信息和 INI 管理器
    mod_registry = ModRegistry()
    ini_manager = IniManager(paths['config_dir'], backup_retention=backup_retention)
    
    # 获取已启用的 mod 列表
    enabled_mods = mod_registry.get_enabled_mods()
    
    if not enabled_mods:
        logger.info("当前没有已启用的 Mod，无需排序\n")
        return
    
    # 获取当前 INI 中的 mod 列表
    current_ini_mods = ini_manager.get_mod_list(ini_mode)
    
    # 检查是否有已启用的 mod 不在 INI 中
    missing_in_ini = [mod for mod in enabled_mods if mod not in current_ini_mods]
    if missing_in_ini:
        logger.warning(f"发现 {len(missing_in_ini)} 个已启用的 Mod 不在 INI 中:")
        for mod_name in missing_in_ini:
            logger.warning(f"  - {mod_registry.get_display_name(mod_name)}")
        logger.warning("这些 Mod 将不会参与排序")
    
    # 只处理在 INI 中的已启用 mod
    mods_to_sort = [mod for mod in enabled_mods if mod in current_ini_mods]
    
    if not mods_to_sort:
        logger.info("=" * 50)
        logger.info("没有可排序的 Mod")
        return
    
    # 首次初始化：检查是否有 order 为 None 的 mod
    needs_init = False
    for mod_name in mods_to_sort:
        mod_info = mod_registry.get_mod_info(mod_name)
        if mod_info and mod_info.get('order') is None:
            needs_init = True
            break
    
    if needs_init:
        logger.info("检测到部分 Mod 未初始化顺序，正在自动初始化...")
        logger.info("=" * 50)
        
        # 按当前 INI 中的顺序初始化 order（从 1 开始）
        # 只初始化在 mods_to_sort 中的 mod
        init_count = 0
        for idx, mod_name in enumerate(current_ini_mods, 1):
            if mod_name in mods_to_sort:
                mod_registry.set_mod_order(mod_name, idx)
                display_name = mod_registry.get_display_name(mod_name)
                logger.info(f"初始化 {display_name}: order = {idx}")
                init_count += 1
        
        logger.info("=" * 50)
        logger.info(f"已初始化 {init_count} 个 Mod 的顺序\n")
    
    # 获取按 order 排序的 mod 列表
    sorted_mods = mod_registry.get_mods_by_order(enabled_only=True)
    sorted_mod_names = [mod_name for mod_name, _ in sorted_mods if mod_name in mods_to_sort]
    
    # 如果排序后的列表与当前列表不一致，使用当前 INI 顺序作为基准
    if not sorted_mod_names or len(sorted_mod_names) != len(mods_to_sort):
        sorted_mod_names = [mod for mod in current_ini_mods if mod in mods_to_sort]
    
    # 在内存中维护当前顺序
    current_order = sorted_mod_names.copy()
    
    def display_mod_list():
        """显示当前 mod 列表"""
        logger.info("当前 Mod 顺序:")
        logger.info("=" * 50)
        for idx, mod_name in enumerate(current_order, 1):
            mod_info = mod_registry.get_mod_info(mod_name)
            order = mod_info.get('order') if mod_info else None
            display_name = mod_registry.get_display_name(mod_name)
            logger.info(f"{idx}. {display_name} (order: {order or 'None'})")
        logger.info("=" * 50)
    
    # 显示初始列表
    display_mod_list()
    
    # 显示操作提示（vim 风格）
    print("\n操作说明:")
    print("  - 输入 \"源序号 目标序号\" 来移动 Mod（例如: 1 6 表示将第1个移动到第6个之前）")
    print("  - 输入 \":w\" 或 \":wq\" 保存并退出")
    print("  - 输入 \":q\" 或 \":q!\" 取消并退出")
    
    # 直接操作循环（完全按照 vim）
    while True:
        user_input = input("\n请输入操作> ").strip()
        print("")
        
        if not user_input:
            continue
        
        # 保存并退出
        if user_input in [':w', ':wq', ':x']:
            break
        
        # 取消并退出
        if user_input in [':q', ':q!']:
            logger.info("已取消排序操作")
            logger.info("=" * 50)
            return
        
        # 解析移动命令：格式为 "源序号 目标序号"（空格分隔）
        parts = user_input.split()
        if len(parts) == 2:
            try:
                move_idx = int(parts[0])
                target_idx = int(parts[1])
                
                if move_idx < 1 or move_idx > len(current_order):
                    logger.warning(f"源序号无效，请输入 1-{len(current_order)} 之间的数字")
                    continue
                
                if target_idx < 1 or target_idx > len(current_order):
                    logger.warning(f"目标序号无效，请输入 1-{len(current_order)} 之间的数字")
                    continue
                
                # 如果移动到同一位置，跳过
                if move_idx == target_idx:
                    logger.info("Mod 已在目标位置")
                    continue
                
                # 获取要移动的 mod
                move_mod = current_order[move_idx - 1]
                
                # 从列表中移除
                current_order.remove(move_mod)
                
                # 计算插入位置（移除后，目标位置的索引需要调整）
                if move_idx < target_idx:
                    # 向后移动：移除后，目标位置索引减1
                    insert_pos = target_idx - 2
                else:
                    # 向前移动：移除后，目标位置索引不变
                    insert_pos = target_idx - 1
                
                # 插入到目标位置
                current_order.insert(insert_pos, move_mod)
                
                display_name = mod_registry.get_display_name(move_mod)
                logger.info(f"已将 {display_name} 移动到位置 {target_idx}")
                
                # 显示更新后的列表
                display_mod_list()
                
            except ValueError:
                logger.warning("请输入有效的数字")
            except Exception as e:
                logger.error(f"移动 Mod 时发生错误: {e}")
        else:
            logger.warning("无效的输入，请输入 \"源序号 目标序号\"、\":w\" 保存或 \":q\" 退出")
    
    # 确认保存
    print("\n是否保存排序结果? (Y/n): ", end='')
    save_confirm = input().strip()
    
    if save_confirm and save_confirm.lower() != 'y':
        logger.info("已取消保存")
        logger.info("=" * 50)
        return
    
    logger.info("正在保存排序结果...")
    logger.info("=" * 50)
    
    # 更新 INI 文件中的顺序
    # 需要保留不在排序列表中的 mod（保持原有顺序）
    all_mods_in_ini = ini_manager.get_mod_list(ini_mode)
    other_mods = [mod for mod in all_mods_in_ini if mod not in mods_to_sort]
    
    # 合并：排序的 mod 在前，其他 mod 在后
    new_order = current_order + other_mods
    
    if ini_manager.reorder_mod_list(ini_mode, new_order):
        # 更新注册信息中所有已启用 mod 的 order 值
        # order 值基于它们在 new_order 中的位置
        updated_count = 0
        for idx, mod_name in enumerate(new_order, 1):
            if mod_name in mods_to_sort:
                mod_registry.set_mod_order(mod_name, idx)
                updated_count += 1
        
        logger.info("=" * 50)
        logger.info("排序保存成功")
        logger.info(f"已更新 {updated_count} 个 Mod 的顺序")
    else:
        logger.error("保存排序失败")


def update_ini_config():
    """更新 Fallout76Custom.ini 配置文件（添加缺失的已启用 mod，删除未启用的 mod）"""
    logger.info("开始更新 Fallout76Custom.ini 配置\n")
    
    # 初始化路径检测器
    path_detector = PathDetector()
    paths = path_detector.get_all_paths()
    
    if not paths['config_dir']:
        logger.error("未找到配置目录")
        return
    
    # 加载配置
    config = load_config()
    ini_mode = config.get('ini_mode', 'sResourceArchive2List')
    backup_retention = config.get('ini_backup_retention', 0)
    
    # 初始化 Mod 注册信息和 INI 管理器
    mod_registry = ModRegistry()
    ini_manager = IniManager(paths['config_dir'], backup_retention=backup_retention)
    
    # 获取已启用的 mod 列表
    enabled_mods = mod_registry.get_enabled_mods()
    
    # 获取当前 INI 中的 mod 列表
    current_ini_mods = ini_manager.get_mod_list(ini_mode)
    
    # 找出需要添加的 mod（已启用但不在 INI 中）
    missing_mods = [mod for mod in enabled_mods if mod not in current_ini_mods]
    
    # 找出需要删除的 mod（在 INI 中但未启用）
    # 只处理注册信息中存在的 mod，忽略注册信息中不存在的 mod（可能是手动添加的）
    disabled_mods = []
    for mod_name in current_ini_mods:
        mod_info = mod_registry.get_mod_info(mod_name)
        if mod_info and not mod_info.get('enabled', False):
            disabled_mods.append(mod_name)
    
    # 如果没有需要更新的内容
    if not missing_mods and not disabled_mods:
        logger.info("所有 Mod 配置已同步，无需更新\n")
        return
    
    # 显示需要更新的内容
    logger.info("需要更新的内容:")
    logger.info("=" * 50)
    
    if missing_mods:
        logger.info(f"需要添加的已启用 Mod ({len(missing_mods)} 个):")
        for idx, mod_name in enumerate(missing_mods, 1):
            mod_info = mod_registry.get_mod_info(mod_name)
            version = mod_info.get('version', '未知') if mod_info else '未知'
            display_name = mod_registry.get_display_name(mod_name)
            logger.info(f"  {idx}. {display_name} (版本: {version})")
    
    if disabled_mods:
        logger.info(f"需要删除的未启用 Mod ({len(disabled_mods)} 个):")
        for idx, mod_name in enumerate(disabled_mods, 1):
            display_name = mod_registry.get_display_name(mod_name)
            logger.info(f"  {idx}. {display_name}")
    
    logger.info("=" * 50)
    
    print("\n是否执行更新? (Y/n): ", end='')
    print("")
    confirm = input().strip()
    
    if confirm and confirm.lower() != 'y':
        logger.info("已取消更新操作")
        return
    
    logger.info("开始更新 INI 配置...")
    logger.info("=" * 50)
    
    added_count = 0
    removed_count = 0
    failed_add_count = 0
    failed_remove_count = 0
    
    # 添加缺失的已启用 mod 和删除未启用的 mod（批量操作）
    with ini_manager:
        # 添加缺失的已启用 mod
        if missing_mods:
            logger.info("添加缺失的已启用 Mod...")
            for mod_name in missing_mods:
                # 检查 mod 是否在注册信息中
                mod_info = mod_registry.get_mod_info(mod_name)
                if not mod_info:
                    logger.warning(f"{mod_name} 不在注册信息中，跳过")
                    failed_add_count += 1
                    continue
                
                # 添加 mod 到 INI 配置
                if ini_manager.add_mod_to_list(mod_name, ini_mode):
                    mod_registry.mark_mod_enabled(mod_name)
                    added_count += 1
                    display_name = mod_registry.get_display_name(mod_name)
                    logger.info(f"已添加: {display_name}")
                else:
                    failed_add_count += 1
                    display_name = mod_registry.get_display_name(mod_name)
                    logger.error(f"添加失败: {display_name}")
        
        # 删除未启用的 mod
        if disabled_mods:
            logger.info("删除未启用的 Mod...")
            for mod_name in disabled_mods:
                # 从 INI 中移除 mod
                if ini_manager.remove_mod_from_list(mod_name, ini_mode):
                    removed_count += 1
                    display_name = mod_registry.get_display_name(mod_name)
                    logger.info(f"已删除: {display_name}")
                else:
                    failed_remove_count += 1
                    display_name = mod_registry.get_display_name(mod_name)
                    logger.error(f"删除失败: {display_name}")
    
    logger.info("=" * 50)
    logger.info(f"更新完成:")
    logger.info(f"  添加: 成功 {added_count} 个, 失败 {failed_add_count} 个")
    logger.info(f"  删除: 成功 {removed_count} 个, 失败 {failed_remove_count} 个")


def open_directories():
    """打开游戏目录和配置目录"""
    logger.info("打开目录功能\n")
    
    # 初始化路径检测器
    path_detector = PathDetector()
    paths = path_detector.get_all_paths()
    
    print("请选择要打开的目录:")
    print("1. 打开游戏目录")
    print("2. 打开配置目录")
    print("0. 返回")
    
    choice = input("\n请选择: ").strip()
    print("")
    
    if choice == '1':
        game_path = paths.get('game_path')
        if not game_path:
            logger.error("未找到游戏路径，请检查 configs/config.json 配置")
            return
        
        if not os.path.exists(game_path):
            logger.error(f"游戏目录不存在: {game_path}")
            return
        
        try:
            os.startfile(game_path)
            logger.info(f"已打开游戏目录: {game_path}")
        except Exception as e:
            logger.error(f"打开游戏目录失败: {e}")
    
    elif choice == '2':
        config_dir = paths.get('config_dir')
        if not config_dir:
            logger.error("未找到配置目录")
            return
        
        if not os.path.exists(config_dir):
            logger.error(f"配置目录不存在: {config_dir}")
            return
        
        try:
            os.startfile(config_dir)
            logger.info(f"已打开配置目录: {config_dir}")
        except Exception as e:
            logger.error(f"打开配置目录失败: {e}")
    
    elif choice == '0':
        return
    else:
        logger.warning("无效的选择")


def remove_mod():
    """删除 Mod"""
    logger.info("准备删除 Mod...\n")
    
    # 初始化 Mod 注册信息
    mod_registry = ModRegistry()
    
    # 获取所有 mod（按 order 排序）
    sorted_mods = mod_registry.get_mods_by_order(enabled_only=False)
    
    if not sorted_mods:
        logger.info("当前没有已注册的 Mod\n")
        return
    
    # 显示所有 mod 列表
    logger.info("已注册的 Mod 列表:")
    logger.info("=" * 50)
    mod_list = []
    for idx, (mod_name, mod_info) in enumerate(sorted_mods, 1):
        display_name = mod_registry.get_display_name(mod_name)
        status = "✓ 已启用" if mod_info.get('enabled', False) else "✗ 未启用"
        version = mod_info.get('version', '未知')
        logger.info(f"{idx}. {display_name} ({status}, 版本: {version})")
        mod_list.append((mod_name, mod_info))
    
    logger.info("=" * 50)
    
    # 用户输入要删除的序号（空格隔开）
    print("\n请输入要删除的 Mod 序号（空格隔开，例如: 1 3 5）:")
    print("按 Enter 取消")
    user_input = input("> ").strip()
    print("")
    
    if not user_input:
        logger.info("已取消删除操作")
        return
    
    # 解析序号
    try:
        indices = [int(x.strip()) for x in user_input.split()]
    except ValueError:
        logger.error("输入格式错误，请输入数字序号，空格隔开")
        return
    
    # 验证序号范围
    if not indices or any(idx < 1 or idx > len(mod_list) for idx in indices):
        logger.error(f"序号无效，请输入 1-{len(mod_list)} 之间的数字")
        return
    
    # 获取要删除的 mod
    mods_to_remove = [mod_list[idx - 1][0] for idx in indices]
    display_names = [mod_registry.get_display_name(mod_name) for mod_name in mods_to_remove]
    
    # 显示将要删除的 mod
    logger.info("\n将要删除以下 Mod:")
    logger.info("=" * 50)
    for display_name in display_names:
        logger.info(f"  - {display_name}")
    logger.info("=" * 50)
    
    # 确认删除
    print("\n确认删除? (y/N): ", end='')
    confirm = input().strip().lower()
    print("")
    
    if confirm != 'y':
        logger.info("已取消删除操作")
        return
    
    # 初始化路径检测器和 INI 管理器
    path_detector = PathDetector()
    paths = path_detector.get_all_paths()
    
    config = load_config()
    ini_mode = config.get('ini_mode', 'sResourceArchive2List')
    backup_retention = config.get('ini_backup_retention', 0)
    
    ini_manager = IniManager(paths['config_dir'], backup_retention=backup_retention) if paths.get('config_dir') else None
    
    # 获取脚本目录
    script_dir = os.path.dirname(os.path.abspath(__file__))
    mods_dir = os.path.join(script_dir, 'mods')
    backups_dir = os.path.join(script_dir, 'backups')
    data_path = paths.get('data_path')
    
    # 开始删除
    logger.info("开始删除 Mod...")
    logger.info("=" * 50)
    
    success_count = 0
    failed_count = 0
    
    for mod_name in mods_to_remove:
        # 在删除之前获取所有需要的信息
        display_name = mod_registry.get_display_name(mod_name)
        mod_info = mod_registry.get_mod_info(mod_name)
        
        try:
            # 1. 从 INI 配置中删除
            if ini_manager:
                if ini_manager.remove_mod_from_list(mod_name, ini_mode):
                    logger.info(f"已从 INI 配置中删除: {display_name}")
                else:
                    logger.warning(f"⚠ 从 INI 配置中删除失败: {display_name}")
            
            # 2. 从注册信息中删除（在删除之前已经获取了所有需要的信息）
            if mod_registry.unregister_mod(mod_name):
                logger.info(f"已从注册信息中删除: {display_name}")
            else:
                logger.warning(f"⚠ 从注册信息中删除失败: {display_name}")
            
            # 3. 删除 mods 目录下的文件夹
            # 从 source_file 提取 mod 文件夹名（去掉扩展名）
            source_file = mod_info.get('source_file') if mod_info else None
            if source_file:
                mod_folder_name = os.path.splitext(source_file)[0]
                mod_folder_path = os.path.join(mods_dir, mod_folder_name)
                
                if os.path.exists(mod_folder_path) and os.path.isdir(mod_folder_path):
                    try:
                        import shutil
                        shutil.rmtree(mod_folder_path)
                        logger.info(f"已删除 mods 文件夹: {mod_folder_name}")
                    except Exception as e:
                        logger.warning(f"⚠ 删除 mods 文件夹失败: {e}")
            
            # 4. 删除 Data 目录中的 mod 文件
            if data_path and mod_name:
                mod_file_path = os.path.join(data_path, mod_name)
                if os.path.exists(mod_file_path) and os.path.isfile(mod_file_path):
                    try:
                        os.remove(mod_file_path)
                        logger.info(f"已删除 Data 目录中的文件: {mod_name}")
                    except Exception as e:
                        logger.warning(f"⚠ 删除 Data 目录中的文件失败: {e}")
            
            # 5. 清理备份文件夹
            if mod_info:
                # 使用 mod 文件名（去掉扩展名）作为备份文件夹名
                backup_mod_name = os.path.splitext(mod_name)[0]
                backup_mod_dir = os.path.join(backups_dir, backup_mod_name)
                
                if os.path.exists(backup_mod_dir) and os.path.isdir(backup_mod_dir):
                    try:
                        import shutil
                        shutil.rmtree(backup_mod_dir)
                        logger.info(f"已清理备份文件夹: {backup_mod_name}")
                    except Exception as e:
                        logger.warning(f"⚠ 清理备份文件夹失败: {e}")
            
            success_count += 1
            logger.info(f"成功删除: {display_name}")
            
        except Exception as e:
            failed_count += 1
            logger.error(f"✗ 删除失败: {display_name} - {e}")
    
    logger.info("=" * 50)
    logger.info(f"删除完成: 成功 {success_count} 个, 失败 {failed_count} 个\n")


def main():
    """主函数"""
    try:
        while True:
            display_menu()
            choice = input("\n请选择操作 (1-9): ").strip()
            print("")
            
            if choice == '1':
                launch_game()
            elif choice == '2':
                install_mods()
            elif choice == '3':
                view_mod_list()
            elif choice == '4':
                check_mod_updates()
            elif choice == '5':
                detect_mod_info()
            elif choice == '6':
                reorder_mods()
            elif choice == '7':
                update_ini_config()
            elif choice == '8':
                remove_mod()
            elif choice == '9':
                open_directories()
            elif choice == '0':
                logger.info("再见!\n")
                logger.info("用户退出程序\n")
                break
            else:
                logger.warning("无效的选择，请输入 0-9\n")
            
            # 等待用户按键继续
            if choice != '0':
                input("\n按 Enter 键继续...\n\n")
    
    except KeyboardInterrupt:
        logger.info("程序被用户中断")
        sys.exit(0)
    except Exception as e:
        logger.critical(f"程序发生错误: {e}", exc_info=True)
        sys.exit(1)


if __name__ == '__main__':
    main()
