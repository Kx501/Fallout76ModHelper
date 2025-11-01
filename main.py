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
            "ini_mode": "sResourceArchive2List",
            "backup_extensions": [".json", ".ini"],
            "ini_backup_retention": 5,
            "default_mod_directory": None,
            "nexus_api": {
                "api_key": "",
                "mod_directory": ""
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
    print("3. 查看启用 Mod")
    print("4. 检查 Mod 更新")
    print("5. 更新 Mod 信息")
    print("6. 修补 Fallout76Custom.ini")
    print("7. 退出")
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
    default_mod_directory = config.get('default_mod_directory')
    
    # 获取 mod 文件夹路径
    mod_folder = None
    if default_mod_directory:
        # 展开环境变量并检查路径
        expanded_path = os.path.expandvars(default_mod_directory)
        if os.path.exists(expanded_path) and os.path.isdir(expanded_path):
            mod_folder = expanded_path
            logger.info(f"使用默认 Mod 目录: {mod_folder}")
        else:
            logger.warning(f"配置的默认 Mod 目录不存在: {expanded_path}")
    
    if not mod_folder:
        print("请输入 Mod 文件夹路径（包含 ZIP 压缩包的文件夹）:")
        mod_folder = input("> ").strip().strip('"').strip("'")
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
    backup_retention = config.get('ini_backup_retention', 5)
    
    # 初始化 Mod 注册表
    mod_registry = ModRegistry()
    
    # 初始化 INI 管理器
    ini_manager = IniManager(paths['config_dir'], backup_retention=backup_retention)
    
    # 初始化 Mod 安装器
    installer = ModInstaller(
        paths['data_path'],
        paths['config_dir'],
        ini_manager,
        mod_registry=mod_registry,
        backup_extensions=backup_extensions
    )
    
    logger.info(f"开始安装 Mod，从文件夹: {mod_folder}")
    logger.info("=" * 50)
    
    result = installer.install_mods_from_folder(mod_folder)
    
    logger.info("=" * 50)
    logger.info(f"安装完成!")
    logger.info(f"成功: {result['success']} 个")
    logger.info(f"失败: {result['failed']} 个")
    
    if result['mods']:
        logger.info(f"已添加到 INI 配置的 Mod 文件:")
        for mod_file in result['mods']:
            logger.info(f"  - {mod_file}")


def view_enabled_mods():
    """查看已启用的 Mod"""
    logger.info("查询启用的 Mod...\n")
    
    # 初始化 Mod 注册表
    mod_registry = ModRegistry()
    
    # 获取已启用的 mod 列表
    enabled_mods = mod_registry.get_enabled_mods()
    
    if not enabled_mods:
        logger.info("当前没有已启用的 Mod\n")
        return
    
    logger.info(f"已启用的 Mod ({len(enabled_mods)} 个):")
    logger.info("=" * 50)
    
    # 加载配置以获取 INI 模式
    config = load_config()
    ini_mode = config.get('ini_mode', 'sResourceArchive2List')
    
    # 初始化路径检测器和 INI 管理器以获取当前 INI 中的 mod
    path_detector = PathDetector()
    paths = path_detector.get_all_paths()
    
    if paths['config_dir']:
        backup_retention = config.get('ini_backup_retention', 5)
        ini_manager = IniManager(paths['config_dir'], backup_retention=backup_retention)
        current_ini_mods = ini_manager.get_mod_list(ini_mode)
    else:
        current_ini_mods = []
    
    # 显示 mod 信息
    for idx, mod_name in enumerate(enabled_mods, 1):
        mod_info = mod_registry.get_mod_info(mod_name)
        
        # 检查是否在 INI 中
        in_ini = mod_name in current_ini_mods
        status = "✓ 已启用" if in_ini else "⚠ 配置丢失"
        
        logger.info(f"{idx}. {mod_name}")
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
    
    logger.info("=" * 50)
    logger.info("Mod 列表查询完成\n")
    
    # 检查是否有丢失的配置
    if current_ini_mods:
        missing_mods = [mod for mod in enabled_mods if mod not in current_ini_mods]
        if missing_mods:
            logger.warning(f"发现 {len(missing_mods)} 个 Mod 的配置丢失\n")
            logger.warning("建议运行 '安装 Mod' 或 '修补 Fallout76Custom.ini' 功能来恢复")
    else:
        # 如果 INI 中没有 mod，说明所有已启用的 mod 都丢失了
        if enabled_mods:
            logger.warning("检测到所有已启用的 Mod 配置丢失\n")
            logger.warning("建议运行 '修补 Fallout76Custom.ini' 功能来恢复")


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
    
    # 初始化 Mod 注册表
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
        
        if not mod_id:
            continue
        
        logger.info(f"检查更新: {mod_name}")
        logger.info(f"Mod ID: {mod_id}, 当前版本: {current_version or '未知'}")
        
        # 获取最新版本信息
        latest_info = nexus_api.get_latest_version(mod_id)
        
        if not latest_info:
            error_mods.append((mod_name, "无法获取更新信息"))
            logger.warning(f"无法获取 {mod_name} 的更新信息")
            continue
        
        latest_version = latest_info.get('version')
        
        if not latest_version:
            error_mods.append((mod_name, "无法识别版本号"))
            logger.warning(f"无法识别 {mod_name} 的最新版本号")
            continue
        
        logger.info(f"{mod_name} 当前版本: {current_version or '未知'}")
        logger.info(f"{mod_name} 最新版本: {latest_version}")
        
        # 比较版本
        if not current_version:
            # 如果没有当前版本号，假设有更新
            updated_mods.append((mod_name, current_version, latest_version, latest_info))
            logger.info(f"{mod_name} 发现新版本: {latest_version}")
        else:
            has_update = nexus_api.compare_versions(current_version, latest_version)
            if has_update:
                updated_mods.append((mod_name, current_version, latest_version, latest_info))
                logger.info(f"{mod_name} 发现新版本: {current_version} -> {latest_version}")
            elif has_update is False:
                no_update_mods.append((mod_name, current_version, latest_version))
                logger.info(f"{mod_name} 已是最新版本")
            else:
                # 无法比较版本（格式不同等）
                if current_version != latest_version:
                    # 版本号字符串不同，可能是有更新
                    updated_mods.append((mod_name, current_version, latest_version, latest_info))
                    logger.info(f"{mod_name} 版本号不同（无法比较）")
                    logger.info(f"当前: {current_version} -> 最新: {latest_version}")
                else:
                    no_update_mods.append((mod_name, current_version, latest_version))
                    logger.info(f"{mod_name} 版本号相同: {current_version}")
    
    logger.info("=" * 50)
    logger.info(f"检查完成: 发现 {len(updated_mods)} 个更新")
    logger.info(f"已是最新: {len(no_update_mods)} 个, 错误: {len(error_mods)} 个")
    
    if updated_mods:
        logger.info("可更新 Mod:")
        for mod_name, old_version, new_version, latest_info in updated_mods:
            mod_url = latest_info.get('mod_url', '')
            logger.info(f"• {mod_name}: {old_version or '未知'} -> {new_version}")
            if mod_url:
                logger.info(f"|__{mod_url}")
    else:
        logger.info(f"✓ 所有 Mod 都已是最新版本\n")
    
    if error_mods:
        logger.warning(f"{len(error_mods)} 个 Mod 检查失败:")
        for mod_name, error_msg in error_mods:
            logger.warning(f"• {mod_name}: {error_msg}")


def detect_mod_info():
    """检测 Mod 信息并更新注册表"""
    logger.info("开始检测 Mod 信息...\n")
    
    # 获取脚本目录下的 mods/ 文件夹
    script_dir = os.path.dirname(os.path.abspath(__file__))
    mods_dir = os.path.join(script_dir, 'mods')
    
    if not os.path.exists(mods_dir) or not os.path.isdir(mods_dir):
        logger.error("mods/ 目录不存在")
        return
    
    # 初始化 Mod 注册表
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
                # 新发现的 mod（不在注册表中）
                # 如果有版本号或 Mod ID 信息，注册它
                if version or nexus_mod_id:
                    mod_registry.register_mod(mod_file, folder_path, version, nexus_mod_id, enabled=False)
                    new_count += 1
                    logger.info(f"新发现 mod: {mod_file}")
                    if version:
                        logger.info(f"  版本号: {version}")
                    if nexus_mod_id:
                        logger.info(f"  Mod ID: {nexus_mod_id}")
                    
    logger.info("=" * 50)
    logger.info(f"Mod 信息检测完成")
    logger.info(f"更新: {updated_count} 个, 新发现: {new_count} 个")


def repair_ini_config():
    """修补 Fallout76Custom.ini 配置文件"""
    logger.info("开始修补 Fallout76Custom.ini 配置\n")
    
    # 初始化路径检测器
    path_detector = PathDetector()
    paths = path_detector.get_all_paths()
    
    if not paths['config_dir']:
        logger.error("未找到配置目录")
        return
    
    # 加载配置
    config = load_config()
    ini_mode = config.get('ini_mode', 'sResourceArchive2List')
    backup_retention = config.get('ini_backup_retention', 5)
    
    # 初始化 Mod 注册表和 INI 管理器
    mod_registry = ModRegistry()
    ini_manager = IniManager(paths['config_dir'], backup_retention=backup_retention)
    
    # 获取已启用的 mod 列表
    enabled_mods = mod_registry.get_enabled_mods()
    
    if not enabled_mods:
        logger.info("当前没有已启用的 Mod，无需修补\n")
        return
    
    # 获取当前 INI 中的 mod 列表
    current_ini_mods = ini_manager.get_mod_list(ini_mode)
    
    # 找出丢失的 mod
    missing_mods = [mod for mod in enabled_mods if mod not in current_ini_mods]
    
    if not missing_mods:
        logger.info("所有已启用的 Mod 配置正常，无需修补\n")
        return
    
    logger.info(f"检测到 {len(missing_mods)} 个已启用的 Mod 配置丢失:")
    logger.info("=" * 50)
    for idx, mod_name in enumerate(missing_mods, 1):
        mod_info = mod_registry.get_mod_info(mod_name)
        version = mod_info.get('version', '未知') if mod_info else '未知'
        logger.info(f"{idx}. {mod_name} (版本: {version})")
    logger.info("=" * 50)
    
    print("\n是否恢复这些 Mod 的配置? (Y/n): ", end='')
    restore = input().strip()
    
    if restore and restore.lower() != 'y':
        logger.info("已取消修补操作")
        return
    
    logger.info(f"开始恢复 {len(missing_mods)} 个丢失的 Mod 配置")
    logger.info("=" * 50)
    
    restored_count = 0
    failed_count = 0
    
    for mod_name in missing_mods:
        # 检查 mod 是否在注册表中
        mod_info = mod_registry.get_mod_info(mod_name)
        if not mod_info:
            logger.warning(f"{mod_name} 不在注册表中，跳过")
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
    logger.info(f"修补完成: 成功 {restored_count} 个, 失败 {failed_count} 个")


def main():
    """主函数"""
    try:
        while True:
            display_menu()
            choice = input("\n请选择操作 (1-7): ").strip()
            print("")
            
            if choice == '1':
                launch_game()
            elif choice == '2':
                install_mods()
            elif choice == '3':
                view_enabled_mods()
            elif choice == '4':
                check_mod_updates()
            elif choice == '5':
                detect_mod_info()
            elif choice == '6':
                repair_ini_config()
            elif choice == '7':
                logger.info("再见!\n")
                logger.info("用户退出程序")
                break
            else:
                logger.warning("无效的选择，请输入 1-7\n")
            
            # 等待用户按键继续
            if choice != '7':
                input("\n按 Enter 键继续...\n\n")
    
    except KeyboardInterrupt:
        logger.info("程序被用户中断")
        sys.exit(0)
    except Exception as e:
        logger.critical(f"程序发生错误: {e}", exc_info=True)
        sys.exit(1)


if __name__ == '__main__':
    main()
