"""
Fallout 76 Mod 安装脚本 - 主入口
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
    print("Fallout 76 Mod 助手")
    print("=" * 50)
    print("1. 启动游戏")
    print("2. 安装 Mod")
    print("3. 查看启用 Mod")
    print("4. 更新 Mod 信息")
    print("5. 修补 Fallout76Custom.ini")
    print("6. 退出")
    print("=" * 50)


def launch_game():
    """启动游戏"""
    logger.info("准备启动游戏...")
    
    # 初始化路径检测器
    path_detector = PathDetector()
    paths = path_detector.get_all_paths()
    
    if not paths['game_path']:
        print("错误: 未找到游戏路径，请检查 configs/config.json 配置")
        logger.error("未找到游戏路径")
        return
    
    # 初始化游戏启动器
    launcher = GameLauncher()
    launcher.set_game_path(paths['game_path'])
    
    print("\n正在启动游戏...")
    if launcher.launch():
        print("游戏启动命令已执行")
        logger.info("游戏启动成功")
    else:
        print("游戏启动失败，请查看日志")
        logger.error("游戏启动失败")


def install_mods():
    """安装 Mod"""
    logger.info("准备安装 Mod...")
    
    # 初始化路径检测器
    path_detector = PathDetector()
    paths = path_detector.get_all_paths()
    
    if not paths['data_path']:
        print("错误: 未找到游戏 Data 目录")
        logger.error("未找到 Data 目录")
        return
    
    if not paths['config_dir']:
        print("错误: 未找到配置目录")
        logger.error("未找到配置目录")
        return
    
    # 获取 mod 文件夹路径
    print("\n请输入 Mod 文件夹路径（包含 ZIP 压缩包的文件夹）:")
    mod_folder = input("> ").strip().strip('"').strip("'")
    
    if not mod_folder:
        print("错误: 路径不能为空")
        return
    
    # 展开环境变量
    mod_folder = os.path.expandvars(mod_folder)
    
    if not os.path.exists(mod_folder):
        print(f"错误: 路径不存在: {mod_folder}")
        logger.error(f"Mod 文件夹不存在: {mod_folder}")
        return
    
    if not os.path.isdir(mod_folder):
        print(f"错误: 不是一个文件夹: {mod_folder}")
        logger.error(f"不是文件夹: {mod_folder}")
        return
    
    # 加载配置
    config = load_config()
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
    
    print(f"\n开始安装 Mod，从文件夹: {mod_folder}")
    print("=" * 50)
    
    result = installer.install_mods_from_folder(mod_folder)
    
    print("\n" + "=" * 50)
    print("安装完成!")
    print(f"成功: {result['success']} 个")
    print(f"失败: {result['failed']} 个")
    
    if result['mods']:
        print(f"\n已添加到 INI 配置的 Mod 文件:")
        for mod_file in result['mods']:
            print(f"  - {mod_file}")
    
    print("=" * 50)


def view_enabled_mods():
    """查看已启用的 Mod"""

    logger.info("查询启用的 Mod...")
    
    # 初始化 Mod 注册表
    mod_registry = ModRegistry()
    
    # 获取已启用的 mod 列表
    enabled_mods = mod_registry.get_enabled_mods()
    
    if not enabled_mods:
        logger.info("当前没有已启用的 Mod")
        return
    
    print(f"\n已启用的 Mod ({len(enabled_mods)} 个):")
    print("=" * 50)
    
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
        
        print(f"\n{idx}. {mod_name}")
        print(f"   状态: {status}")
        
        if mod_info:
            if mod_info.get('version'):
                print(f"   版本: {mod_info['version']}")
            if mod_info.get('install_date'):
                from datetime import datetime
                try:
                    install_date = datetime.fromisoformat(mod_info['install_date'])
                    print(f"   安装时间: {install_date.strftime('%Y-%m-%d %H:%M:%S')}")
                except:
                    print(f"   安装时间: {mod_info['install_date']}")
            if mod_info.get('source_file'):
                print(f"   来源文件: {mod_info['source_file']}")
    
    print("\n" + "=" * 50)
    
    # 检查是否有丢失的配置
    if current_ini_mods:
        missing_mods = [mod for mod in enabled_mods if mod not in current_ini_mods]
        if missing_mods:
            print(f"\n警告: 发现 {len(missing_mods)} 个 Mod 的配置丢失")
            print("建议运行 '安装 Mod' 或 '修补 Fallout76Custom.ini' 功能来恢复")
    else:
        # 如果 INI 中没有 mod，说明所有已启用的 mod 都丢失了
        if enabled_mods:
            print(f"\n警告: 检测到所有已启用的 Mod 配置丢失")
            print("建议运行 '修补 Fallout76Custom.ini' 功能来恢复")


def detect_mod_info():
    """检测 Mod 信息并更新注册表"""
    logger.info("开始检测 Mod 信息...")
    
    # 获取脚本目录下的 mods/ 文件夹
    script_dir = os.path.dirname(os.path.abspath(__file__))
    mods_dir = os.path.join(script_dir, 'mods')
    
    if not os.path.exists(mods_dir) or not os.path.isdir(mods_dir):
        print("\n错误: mods/ 目录不存在")
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
        print("\nmods/ 目录下没有 Mod 子文件夹")
        return
    
    print(f"\n检测到 {len(mod_folders)} 个 Mod 文件夹")
    print("=" * 50)
    
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
                    logger.info(f"更新信息 {mod_file}  {'  '.join(update_parts)}")
            else:
                # 新发现的 mod（不在注册表中）
                # 如果有版本号或 Mod ID 信息，注册它
                if version or nexus_mod_id:
                    mod_registry.register_mod(mod_file, folder_path, version, nexus_mod_id, enabled=False)
                    new_count += 1
                    new_parts = []
                    if version:
                        new_parts.append(f"版本号: {version}")
                    if nexus_mod_id:
                        new_parts.append(f"Mod ID: {nexus_mod_id}")
                    logger.info(f"新发现 mod {mod_file}  {'  '.join(new_parts)}")
                    
    logger.info(f"Mod 信息检测完成: 更新 {updated_count} 个, 新发现 {new_count} 个")
    print("=" * 50)
    print(f"\n检测完成: 更新 {updated_count} 个, 新发现 {new_count} 个")


def repair_ini_config():
    """修补 Fallout76Custom.ini 配置文件"""
    logger.info("开始修补 Fallout76Custom.ini 配置")
    
    # 初始化路径检测器
    path_detector = PathDetector()
    paths = path_detector.get_all_paths()
    
    if not paths['config_dir']:
        print("错误: 未找到配置目录")
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
        print("\n当前没有已启用的 Mod，无需修补")
        return
    
    # 获取当前 INI 中的 mod 列表
    current_ini_mods = ini_manager.get_mod_list(ini_mode)
    
    # 找出丢失的 mod
    missing_mods = [mod for mod in enabled_mods if mod not in current_ini_mods]
    
    if not missing_mods:
        print("\n所有已启用的 Mod 配置正常，无需修补")
        return
    
    print(f"\n检测到 {len(missing_mods)} 个已启用的 Mod 配置丢失:")
    print("=" * 50)
    for idx, mod_name in enumerate(missing_mods, 1):
        mod_info = mod_registry.get_mod_info(mod_name)
        version = mod_info.get('version', '未知') if mod_info else '未知'
        print(f"{idx}. {mod_name} (版本: {version})")
    print("=" * 50)
    
    print("\n是否恢复这些 Mod 的配置? (Y/n): ", end='')
    restore = input().strip()
    
    if restore and restore.lower() != 'y':
        print("已取消修补操作")
        return
    
    logger.info(f"开始恢复 {len(missing_mods)} 个丢失的 Mod 配置")
    print(f"\n正在修补 {len(missing_mods)} 个 Mod 的配置...")
    print("=" * 50)
    
    restored_count = 0
    failed_count = 0
    
    for mod_name in missing_mods:
        # 检查 mod 是否在注册表中
        mod_info = mod_registry.get_mod_info(mod_name)
        if not mod_info:
            print(f"⚠ {mod_name} (不在注册表中，跳过)")
            failed_count += 1
            continue
        
        # 添加 mod 到 INI 配置
        if ini_manager.add_mod_to_list(mod_name, ini_mode):
            mod_registry.mark_mod_enabled(mod_name)
            restored_count += 1
            print(f"✓ {mod_name}")
        else:
            print(f"✗ {mod_name} (失败)")
            failed_count += 1
    
    logger.info(f"修补完成: 成功 {restored_count} 个, 失败 {failed_count} 个")
    print("=" * 50)
    print(f"修补完成: 成功 {restored_count} 个, 失败 {failed_count} 个")


def main():
    """主函数"""
    try:
        while True:
            display_menu()
            choice = input("\n请选择操作 (1-6): ").strip()
            
            if choice == '1':
                launch_game()
            elif choice == '2':
                install_mods()
            elif choice == '3':
                view_enabled_mods()
            elif choice == '4':
                detect_mod_info()
            elif choice == '5':
                repair_ini_config()
            elif choice == '6':
                print("\n再见!")
                logger.info("用户退出程序")
                break
            else:
                print("\n无效的选择，请输入 1-6")
            
            # 等待用户按键继续
            if choice != '6':
                input("\n按 Enter 键继续...")
    
    except KeyboardInterrupt:
        print("\n\n程序被用户中断")
        logger.info("程序被用户中断")
        sys.exit(0)
    except Exception as e:
        logger.critical(f"程序发生错误: {e}", exc_info=True)
        print(f"\n发生错误: {e}")
        sys.exit(1)


if __name__ == '__main__':
    main()

