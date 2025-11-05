"""
Mod 安装模块 - 批量安装 mod 压缩包
"""
import os
import sys
import zipfile
import shutil
from pathlib import Path
from logger import get_logger
import json

try:
    import py7zr
    HAS_7Z_SUPPORT = True
except ImportError:
    HAS_7Z_SUPPORT = False

try:
    import rarfile
    HAS_RAR_SUPPORT = True
except ImportError:
    HAS_RAR_SUPPORT = False

logger = get_logger()


class ModInstaller:
    """Mod 安装器"""
    
    def __init__(self, data_path, config_dir, ini_manager, mod_registry=None, backup_extensions=None, game_path=None):
        """
        初始化 Mod 安装器
        
        Args:
            data_path: Data 目录路径
            config_dir: 配置目录路径（用于备份）
            ini_manager: IniManager 实例
            mod_registry: ModRegistry 实例（用于记录 mod 信息）
            backup_extensions: 需要备份的文件扩展名列表
            game_path: 游戏主目录路径（用于特殊模组安装位置）
        """
        self.data_path = data_path
        self.config_dir = config_dir
        self.ini_manager = ini_manager
        self.mod_registry = mod_registry
        self.backup_extensions = backup_extensions or ['.json', '.ini']
        self.game_path = game_path
        
        # Mod 解压目录（脚本所在目录的 mods/ 文件夹）
        script_dir = os.path.dirname(os.path.abspath(__file__))
        self.mods_dir = os.path.join(script_dir, 'mods')
        os.makedirs(self.mods_dir, exist_ok=True)
        
        # 备份目录（脚本所在目录的 backups/ 文件夹）
        self.backup_dir = os.path.join(script_dir, 'backups')
        os.makedirs(self.backup_dir, exist_ok=True)
        
        # 从配置文件读取配置
        try:
            import json
            config_path = os.path.join(script_dir, 'configs', 'config.json')
            with open(config_path, 'r', encoding='utf-8') as f:
                config = json.load(f)
            self.backup_retention = config.get('ini_backup_retention', 5)
            self.default_install_method = config.get('default_install_method', 'direct')
            self.special_mod_install_paths = config.get('special_mod_install_paths', {})
        except:
            self.backup_retention = 5
            self.default_install_method = 'direct'
            self.special_mod_install_paths = {}
    
    def _should_backup(self, file_path):
        """
        判断文件是否需要备份
        
        Args:
            file_path: 文件路径
        
        Returns:
            是否需要备份
        """
        ext = os.path.splitext(file_path)[1].lower()
        return ext in self.backup_extensions
    
    def _backup_file(self, file_path, mod_name=None):
        """
        备份文件到 backups/ 文件夹的子文件夹
        
        Args:
            file_path: 要备份的文件路径（Data 目录中的文件）
            mod_name: Mod 名称（用于创建子文件夹），如果为 None 则从文件路径推断
        
        Returns:
            备份文件路径，失败返回 None
        """
        try:
            if not os.path.exists(file_path):
                return None
            
            from datetime import datetime
            filename = os.path.basename(file_path)
            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
            
            # 如果没有提供 mod_name，尝试从文件名推断或使用默认名称
            if not mod_name:
                # 尝试从文件名提取 mod 名称（去掉扩展名）
                mod_name = os.path.splitext(filename)[0]
            
            # 创建 mod 专用的备份子文件夹
            mod_backup_dir = os.path.join(self.backup_dir, mod_name)
            os.makedirs(mod_backup_dir, exist_ok=True)
            
            backup_name = f"{timestamp}_{filename}"
            backup_path = os.path.join(mod_backup_dir, backup_name)
            
            shutil.copy2(file_path, backup_path)
            logger.debug(f"备份文件: {file_path} -> {backup_path}")
            
            # 清理旧备份
            self._cleanup_mod_backups(mod_backup_dir)
            
            return backup_path
        except Exception as e:
            logger.warning(f"备份文件失败 {file_path}: {e}")
            return None
    
    def _cleanup_mod_backups(self, mod_backup_dir):
        """
        清理 mod 备份文件夹中的旧备份，只保留最近的 N 个
        
        Args:
            mod_backup_dir: Mod 备份文件夹路径
        """
        try:
            if not os.path.exists(mod_backup_dir):
                return
            
            # 获取文件夹内所有备份文件
            backup_files = [f for f in os.listdir(mod_backup_dir) 
                          if os.path.isfile(os.path.join(mod_backup_dir, f))]
            
            if len(backup_files) <= self.backup_retention:
                return
            
            # 按修改时间排序（最新的在前）
            full_paths = [os.path.join(mod_backup_dir, f) for f in backup_files]
            full_paths.sort(key=os.path.getmtime, reverse=True)
            
            # 删除多余的备份
            to_remove = full_paths[self.backup_retention:]
            for backup in to_remove:
                try:
                    os.remove(backup)
                    logger.debug(f"删除旧备份: {backup}")
                except Exception as e:
                    logger.warning(f"删除旧备份失败 {backup}: {e}")
        
        except Exception as e:
            logger.warning(f"清理 mod 备份失败 {mod_backup_dir}: {e}")
    
    def _extract_zip(self, zip_path, base_extract_dir):
        """
        解压 ZIP 文件到指定目录的子文件夹中
        
        每个 ZIP 文件会解压到 mods/ 下的一个独立子文件夹中，文件夹名基于 ZIP 文件名
        
        Args:
            zip_path: ZIP 文件路径
            base_extract_dir: 基础解压目录（mods/）
        
        Returns:
            (解压文件列表, 子文件夹路径)，失败返回 (None, None)
        """
        try:
            # 基于 ZIP 文件名创建子文件夹名（去掉扩展名）
            zip_name = os.path.basename(zip_path)
            folder_name = os.path.splitext(zip_name)[0]
            
            # 创建子文件夹路径
            mod_subfolder = os.path.join(base_extract_dir, folder_name)
            
            # 确保子文件夹存在
            os.makedirs(mod_subfolder, exist_ok=True)
            
            extracted_files = []
            with zipfile.ZipFile(zip_path, 'r') as zip_ref:
                # 获取所有文件信息
                file_list = zip_ref.namelist()
                
                # 将所有文件提取到子文件夹中（不保持 ZIP 内的子目录结构）
                for file_name in file_list:
                    if file_name.endswith('/'):  # 跳过目录
                        continue
                    
                    # 获取文件名（去除路径）
                    base_name = os.path.basename(file_name)
                    if not base_name:  # 跳过空文件名
                        continue
                    
                    target_path = os.path.join(mod_subfolder, base_name)
                    
                    # 提取单个文件
                    with zip_ref.open(file_name) as source:
                        with open(target_path, 'wb') as target:
                            target.write(source.read())
                    
                    extracted_files.append(target_path)
                
                logger.debug(f"从 {zip_path} 解压了 {len(extracted_files)} 个文件到 {mod_subfolder}")
                return extracted_files, mod_subfolder
        except zipfile.BadZipFile:
            logger.error(f"无效的 ZIP 文件: {zip_path}")
            return None, None
        except Exception as e:
            logger.error(f"解压 ZIP 文件失败 {zip_path}: {e}")
            return None, None
    
    def _extract_7z(self, archive_path, base_extract_dir):
        """
        解压 7z 文件到指定目录的子文件夹中
        
        每个 7z 文件会解压到 mods/ 下的一个独立子文件夹中，文件夹名基于 7z 文件名
        
        Args:
            archive_path: 7z 文件路径
            base_extract_dir: 基础解压目录（mods/）
        
        Returns:
            (解压文件列表, 子文件夹路径)，失败返回 (None, None)
        """
        if not HAS_7Z_SUPPORT:
            logger.error("py7zr 库未安装，无法解压 7z 文件。请运行: pip install py7zr")
            return None, None
        
        try:
            # 基于 7z 文件名创建子文件夹名（去掉扩展名）
            archive_name = os.path.basename(archive_path)
            folder_name = os.path.splitext(archive_name)[0]
            
            # 创建子文件夹路径
            mod_subfolder = os.path.join(base_extract_dir, folder_name)
            
            # 确保子文件夹存在
            os.makedirs(mod_subfolder, exist_ok=True)
            
            extracted_files = []
            with py7zr.SevenZipFile(archive_path, mode='r') as archive:
                # 获取所有文件信息
                file_list = archive.getnames()
                
                # 先解压所有文件到临时目录（保持原有目录结构）
                temp_extract_dir = os.path.join(mod_subfolder, '_temp')
                os.makedirs(temp_extract_dir, exist_ok=True)
                archive.extractall(path=temp_extract_dir)
                
                # 遍历所有文件，移动到目标位置（不保持子目录结构）
                for root, dirs, files in os.walk(temp_extract_dir):
                    for file_name in files:
                        source_file = os.path.join(root, file_name)
                        # 目标路径：直接放在 mod_subfolder 中
                        target_path = os.path.join(mod_subfolder, file_name)
                        
                        # 如果目标文件已存在，先删除
                        if os.path.exists(target_path):
                            os.remove(target_path)
                        
                        # 移动文件到目标位置
                        shutil.move(source_file, target_path)
                        extracted_files.append(target_path)
                
                # 清理临时目录
                try:
                    shutil.rmtree(temp_extract_dir)
                except:
                    pass
                
                logger.debug(f"从 {archive_path} 解压了 {len(extracted_files)} 个文件到 {mod_subfolder}")
                return extracted_files, mod_subfolder
        except Exception as e:
            logger.error(f"解压 7z 文件失败 {archive_path}: {e}")
            return None, None
    
    def _find_unrar_executable(self):
        """
        尝试查找系统中的 unrar 可执行文件
        
        Returns:
            unrar 可执行文件路径，如果未找到返回 None
        """
        # 首先检查 PATH 中是否有 unrar
        unrar_path = shutil.which('unrar')
        if unrar_path:
            return unrar_path
        
        unrar64_path = shutil.which('unrar64')
        if unrar64_path:
            return unrar64_path
        
        # 检查常见的 WinRAR 安装路径（WinRAR 通常包含 unrar.exe）
        if sys.platform == 'win32':
            common_paths = [
                r'C:\Program Files\WinRAR\unrar.exe',
                r'C:\Program Files (x86)\WinRAR\unrar.exe',
                r'C:\Program Files\WinRAR\UnRAR.exe',
                r'C:\Program Files (x86)\WinRAR\UnRAR.exe',
            ]
            
            # 也检查环境变量中的路径
            program_files = os.environ.get('ProgramFiles', '')
            program_files_x86 = os.environ.get('ProgramFiles(x86)', '')
            if program_files:
                common_paths.extend([
                    os.path.join(program_files, 'WinRAR', 'unrar.exe'),
                    os.path.join(program_files, 'WinRAR', 'UnRAR.exe'),
                ])
            if program_files_x86:
                common_paths.extend([
                    os.path.join(program_files_x86, 'WinRAR', 'unrar.exe'),
                    os.path.join(program_files_x86, 'WinRAR', 'UnRAR.exe'),
                ])
            
            for path in common_paths:
                if os.path.exists(path) and os.path.isfile(path):
                    return path
        
        return None
    
    def _extract_rar(self, archive_path, base_extract_dir):
        """
        解压 RAR 文件到指定目录的子文件夹中
        
        每个 RAR 文件会解压到 mods/ 下的一个独立子文件夹中，文件夹名基于 RAR 文件名
        
        Args:
            archive_path: RAR 文件路径
            base_extract_dir: 基础解压目录（mods/）
        
        Returns:
            (解压文件列表, 子文件夹路径)，失败返回 (None, None)
        """
        if not HAS_RAR_SUPPORT:
            logger.error("rarfile 库未安装，无法解压 RAR 文件。请运行: pip install rarfile")
            return None, None
        
        # 尝试自动查找 unrar 可执行文件
        unrar_path = self._find_unrar_executable()
        if unrar_path:
            rarfile.UNRAR_TOOL = unrar_path
            logger.debug(f"找到 unrar 工具: {unrar_path}")
        
        try:
            # 基于 RAR 文件名创建子文件夹名（去掉扩展名）
            archive_name = os.path.basename(archive_path)
            folder_name = os.path.splitext(archive_name)[0]
            
            # 创建子文件夹路径
            mod_subfolder = os.path.join(base_extract_dir, folder_name)
            
            # 确保子文件夹存在
            os.makedirs(mod_subfolder, exist_ok=True)
            
            extracted_files = []
            with rarfile.RarFile(archive_path, 'r') as archive:
                # 获取所有文件信息
                file_list = archive.namelist()
                
                # 先解压所有文件到临时目录（保持原有目录结构）
                temp_extract_dir = os.path.join(mod_subfolder, '_temp')
                os.makedirs(temp_extract_dir, exist_ok=True)
                archive.extractall(path=temp_extract_dir)
                
                # 遍历所有文件，移动到目标位置（不保持子目录结构）
                for root, dirs, files in os.walk(temp_extract_dir):
                    for file_name in files:
                        source_file = os.path.join(root, file_name)
                        # 目标路径：直接放在 mod_subfolder 中
                        target_path = os.path.join(mod_subfolder, file_name)
                        
                        # 如果目标文件已存在，先删除
                        if os.path.exists(target_path):
                            os.remove(target_path)
                        
                        # 移动文件到目标位置
                        shutil.move(source_file, target_path)
                        extracted_files.append(target_path)
                
                # 清理临时目录
                try:
                    shutil.rmtree(temp_extract_dir)
                except:
                    pass
                
                logger.debug(f"从 {archive_path} 解压了 {len(extracted_files)} 个文件到 {mod_subfolder}")
                return extracted_files, mod_subfolder
        except rarfile.RarCannotExec:
            logger.error("=" * 50)
            logger.error("无法找到 unrar 工具，无法解压 RAR 文件。")
            logger.error("")
            logger.error("解决方案:")
            logger.error("1. WinRAR 用户: WinRAR 安装目录通常包含 unrar.exe")
            logger.error("   - 检查: C:\\Program Files\\WinRAR\\unrar.exe")
            logger.error("   - 或: C:\\Program Files (x86)\\WinRAR\\unrar.exe")
            logger.error("   - 将 unrar.exe 所在目录添加到系统 PATH 环境变量")
            logger.error("")
            logger.error("2. 单独安装 unrar:")
            logger.error("   - 下载: https://www.rarlab.com/rar_add.htm")
            logger.error("   - 解压 unrar.exe 到任意目录，并添加到 PATH")
            logger.error("")
            logger.error("3. 使用其他压缩格式: 将 RAR 文件转换为 ZIP 或 7Z 格式")
            logger.error("=" * 50)
            return None, None
        except rarfile.BadRarFile:
            logger.error(f"无效的 RAR 文件: {archive_path}")
            return None, None
        except Exception as e:
            logger.error(f"解压 RAR 文件失败 {archive_path}: {e}")
            return None, None
    
    def _get_mod_install_path(self, archive_name):
        """
        获取模组的安装路径（特殊模组或默认Data目录）
        
        Args:
            archive_name: 压缩包文件名
        
        Returns:
            目标安装目录路径，如果是特殊模组返回特殊路径，否则返回data_path
        """
        if not self.mod_registry:
            return self.data_path
        
        # 提取模组名
        mod_name = self.mod_registry.extract_mod_name_from_filename(archive_name)
        if not mod_name:
            return self.data_path
        
        # 检查是否为特殊模组（不区分大小写）
        for config_mod_name, install_path in self.special_mod_install_paths.items():
            if mod_name.lower() == config_mod_name.lower():
                # 构建完整路径
                if install_path == ".":
                    # 游戏主目录
                    if self.game_path:
                        return self.game_path
                    else:
                        logger.warning(f"特殊模组 {mod_name} 需要安装到游戏主目录，但游戏路径未配置")
                        return self.data_path
                else:
                    # 游戏主目录下的子目录
                    if self.game_path:
                        full_path = os.path.join(self.game_path, install_path)
                        return full_path
                    else:
                        logger.warning(f"特殊模组 {mod_name} 需要安装到 {install_path}，但游戏路径未配置")
                        return self.data_path
        
        return self.data_path
    
    def _get_mod_install_method(self, mod_filename, user_choice=None):
        """
        获取模组的安装方式
        
        Args:
            mod_filename: mod文件名（如 "ModName.ba2"）
            user_choice: 用户选择的安装方式（可选）
        
        Returns:
            实际使用的安装方式（"direct" 或 "copy"）
        """
        # 优先级：用户选择 > 注册表中的install_method > default_install_method
        if user_choice:
            return user_choice
        
        if self.mod_registry:
            mod_info = self.mod_registry.get_mod_info(mod_filename)
            if mod_info and mod_info.get('install_method'):
                return mod_info['install_method']
        
        return self.default_install_method
    
    def _install_direct(self, extracted_files, mod_subfolder, target_dir, mod_name=None):
        """
        方式1：直接将文件从解压文件夹移动到目标目录（保留文件夹）
        
        Args:
            extracted_files: 解压的文件列表
            mod_subfolder: 解压文件夹路径
            target_dir: 目标目录路径
            mod_name: Mod 名称（用于备份时创建子文件夹）
        
        Returns:
            移动的文件路径列表
        """
        moved_files = []
        
        try:
            # 确保目标目录存在
            os.makedirs(target_dir, exist_ok=True)
            
            for source_file in extracted_files:
                filename = os.path.basename(source_file)
                target_path = os.path.join(target_dir, filename)
                
                # 如果目标文件已存在且需要备份，先备份
                if os.path.exists(target_path) and self._should_backup(target_path):
                    if not mod_name:
                        mod_name = os.path.splitext(filename)[0]
                    self._backup_file(target_path, mod_name)
                
                # 移动文件（保留元数据）
                shutil.move(source_file, target_path)
                moved_files.append(target_path)
                logger.debug(f"移动文件到目标目录: {target_path}")
            
            logger.info(f"已移动 {len(moved_files)} 个文件到 {target_dir}（保留解压文件夹）")
            return moved_files
        except Exception as e:
            logger.error(f"移动文件到目标目录失败: {e}")
            return moved_files
    
    def _copy_to_data(self, source_file, mod_name=None, target_dir=None):
        """
        方式2：复制文件到目标目录
        
        Args:
            source_file: 源文件路径
            mod_name: Mod 名称（用于备份时创建子文件夹）
            target_dir: 目标目录路径（如果为None则使用data_path）
        
        Returns:
            目标文件路径，失败返回 None
        """
        if target_dir is None:
            target_dir = self.data_path
        
        try:
            filename = os.path.basename(source_file)
            target_path = os.path.join(target_dir, filename)
            
            # 确保目标目录存在
            os.makedirs(target_dir, exist_ok=True)
            
            # 如果目标文件已存在且需要备份，先备份
            if os.path.exists(target_path) and self._should_backup(target_path):
                # 使用文件名的基名作为 mod_name（如果没有提供）
                if not mod_name:
                    mod_name = os.path.splitext(filename)[0]
                self._backup_file(target_path, mod_name)
            
            # 复制文件（保留元数据）
            shutil.copy2(source_file, target_path)
            logger.debug(f"复制文件到目标目录: {target_path}")
            return target_path
        except Exception as e:
            logger.error(f"复制文件到目标目录失败 {source_file}: {e}")
            return None
    
    
    def _collect_mod_files(self, extracted_files):
        """
        收集 mod 文件（.ba2 等），用于 INI 配置
        
        Args:
            extracted_files: 解压的文件列表
        
        Returns:
            mod 文件名列表（如 ["ModName.ba2", ...]）
        """
        mod_files = []
        mod_extensions = ['.ba2', '.esm', '.esp']
        
        for file_path in extracted_files:
            filename = os.path.basename(file_path)
            ext = os.path.splitext(filename)[1].lower()
            if ext in mod_extensions:
                mod_files.append(filename)
        
        return mod_files
    
    def install_mods_from_folder(self, mod_folder_path, user_choices=None, archive_files=None):
        """
        从文件夹批量安装 mod
        
        Args:
            mod_folder_path: mod 文件夹路径
            user_choices: 用户选择的安装方式字典 {archive_name: "direct"/"copy"}
            archive_files: 已扫描的压缩包文件列表（完整路径），如果为None则自动扫描
        
        Returns:
            安装结果统计字典
        """
        if user_choices is None:
            user_choices = {}
        if not os.path.exists(mod_folder_path) or not os.path.isdir(mod_folder_path):
            logger.error(f"Mod 文件夹不存在: {mod_folder_path}")
            return {'success': 0, 'failed': 0, 'mods': []}
        
        # 如果未提供文件列表，则扫描文件夹
        if archive_files is None:
            logger.info(f"开始扫描 Mod 文件夹: {mod_folder_path}")
            archive_files = []
            for item in os.listdir(mod_folder_path):
                item_path = os.path.join(mod_folder_path, item)
                item_lower = item.lower()
                if os.path.isfile(item_path) and (item_lower.endswith('.zip') or item_lower.endswith('.7z') or item_lower.endswith('.rar')):
                    archive_files.append(item_path)
            
            if not archive_files:
                logger.warning(f"未找到压缩包文件 (.zip, .7z 或 .rar): {mod_folder_path}")
                return {'success': 0, 'failed': 0, 'mods': []}
            
            zip_count = sum(1 for f in archive_files if f.lower().endswith('.zip'))
            sevenz_count = sum(1 for f in archive_files if f.lower().endswith('.7z'))
            rar_count = sum(1 for f in archive_files if f.lower().endswith('.rar'))
            logger.info(f"找到 {len(archive_files)} 个压缩包文件 (ZIP: {zip_count}, 7z: {sevenz_count}, RAR: {rar_count})")
        
        # 获取配置文件中的 ini_mode 并在开始前同步一次
        try:
            script_dir = os.path.dirname(os.path.abspath(__file__))
            config_path = os.path.join(script_dir, 'configs', 'config.json')
            with open(config_path, 'r', encoding='utf-8') as f:
                config = json.load(f)
            ini_mode = config.get('ini_mode', 'sResourceArchive2List')
        except:
            ini_mode = 'sResourceArchive2List'
        
        # 在开始安装前同步 INI 模式（只执行一次）
        logger.info(f"检查并同步 INI 模式到: {ini_mode}")
        self.ini_manager.sync_mode(ini_mode)
        
        # 检查是否有已启用的 mod 丢失了配置
        if self.mod_registry:
            current_ini_mods = self.ini_manager.get_mod_list(ini_mode)
            missing_mods = self.mod_registry.check_missing_mods(current_ini_mods)
            
            if missing_mods:
                logger.warning(f"检测到 {len(missing_mods)} 个已启用的 mod 在 INI 配置中丢失")
                print(f"\n警告: 检测到 {len(missing_mods)} 个已启用的 mod 配置丢失:")
                for mod in missing_mods:
                    print(f"  - {mod}")
                
                print("\n是否自动恢复这些 mod 的配置? (Y/n): ", end='')
                print("")
                restore = input().strip().lower()
                
                if restore == 'y':
                    restored_count = 0
                    for mod_name in missing_mods:
                        if self.ini_manager.add_mod_to_list(mod_name, ini_mode):
                            self.mod_registry.mark_mod_enabled(mod_name)
                            restored_count += 1
                            logger.info(f"已恢复 mod 配置: {mod_name}")
                    
                    if restored_count > 0:
                        print(f"已恢复 {restored_count} 个 mod 的配置")
                else:
                    logger.info("用户选择不恢复丢失的 mod 配置")
        
        success_count = 0
        failed_count = 0
        installed_mods = []
        
        for archive_path in archive_files:
            archive_name = os.path.basename(archive_path)
            logger.info(f"正在安装: {archive_name}")
            
            try:
                # 根据文件扩展名选择解压方法
                if archive_path.lower().endswith('.zip'):
                    extracted_files, mod_subfolder = self._extract_zip(archive_path, self.mods_dir)
                elif archive_path.lower().endswith('.7z'):
                    extracted_files, mod_subfolder = self._extract_7z(archive_path, self.mods_dir)
                elif archive_path.lower().endswith('.rar'):
                    extracted_files, mod_subfolder = self._extract_rar(archive_path, self.mods_dir)
                else:
                    logger.error(f"不支持的压缩包格式: {archive_name}")
                    failed_count += 1
                    continue
                
                if not extracted_files:
                    logger.error(f"解压失败: {archive_name}")
                    failed_count += 1
                    continue
                
                logger.debug(f"Mod 解压到子文件夹: {mod_subfolder}")
                
                # 获取 mod 名称（用于备份文件夹命名）
                mod_name = os.path.basename(mod_subfolder)
                
                # 获取目标安装目录（特殊模组或默认Data目录）
                target_dir = self._get_mod_install_path(archive_name)
                
                # 收集 mod 文件（用于确定安装方式）
                mod_files = self._collect_mod_files(extracted_files)
                if not mod_files:
                    logger.warning(f"没有找到 mod 文件: {archive_name}")
                    failed_count += 1
                    continue
                
                # 确定安装方式（使用第一个mod文件作为代表）
                mod_file = mod_files[0]
                # user_choices中的key是文件名（不含路径），archive_name已经是basename了
                user_choice = user_choices.get(archive_name)
                install_method = self._get_mod_install_method(mod_file, user_choice)
                
                # 根据安装方式安装文件
                installed_files = []
                if install_method == "direct":
                    # 方式1：直接移动文件
                    installed_files = self._install_direct(extracted_files, mod_subfolder, target_dir, mod_name)
                else:
                    # 方式2：复制文件
                    for extracted_file in extracted_files:
                        copied_path = self._copy_to_data(extracted_file, mod_name, target_dir)
                        if copied_path:
                            installed_files.append(copied_path)
                
                if not installed_files:
                    logger.warning(f"没有文件被安装到目标目录: {archive_name}")
                
                # 添加 mod 文件到 INI（只处理.ba2/.esm/.esp文件）
                for mod_file in mod_files:
                    if self.ini_manager.add_mod_to_list(mod_file, ini_mode):
                        installed_mods.append(mod_file)
                        logger.info(f"添加 mod 到 INI: {mod_file}")
                        
                        # 注册 mod 到注册表（记录版本号等信息），并标记为已启用
                        if self.mod_registry:
                            version = None  # 由 registry 自动检测
                            mod_info = self.mod_registry.register_mod(mod_file, archive_path, version, enabled=True)
                            # 保存安装方式到注册表（使用本次安装确定的安装方式）
                            if mod_info:
                                # 如果安装时确定了新的安装方式，更新注册表
                                # 注意：对于已存在的mod，register_mod会保留旧的install_method
                                # 但这里我们要使用本次安装确定的install_method
                                mod_info['install_method'] = install_method
                                self.mod_registry._save_registry()
                
                # 删除原压缩包
                try:
                    os.remove(archive_path)
                    logger.info(f"已删除压缩包: {archive_name}")
                except Exception as e:
                    logger.warning(f"删除压缩包失败 {archive_name}: {e}")
                
                success_count += 1
                logger.info(f"成功安装: {archive_name}")
                
            except Exception as e:
                logger.error(f"安装 mod 失败 {archive_name}: {e}")
                failed_count += 1
        
        result = {
            'success': success_count,
            'failed': failed_count,
            'mods': installed_mods
        }
        
        return result

