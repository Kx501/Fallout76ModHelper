"""
Mod 安装模块 - 批量安装 mod 压缩包
"""
import os
import zipfile
import shutil
from pathlib import Path
from logger import get_logger
import json

logger = get_logger()


class ModInstaller:
    """Mod 安装器"""
    
    def __init__(self, data_path, config_dir, ini_manager, mod_registry=None, backup_extensions=None):
        """
        初始化 Mod 安装器
        
        Args:
            data_path: Data 目录路径
            config_dir: 配置目录路径（用于备份）
            ini_manager: IniManager 实例
            mod_registry: ModRegistry 实例（用于记录 mod 信息）
            backup_extensions: 需要备份的文件扩展名列表
        """
        self.data_path = data_path
        self.config_dir = config_dir
        self.ini_manager = ini_manager
        self.mod_registry = mod_registry
        self.backup_extensions = backup_extensions or ['.json', '.ini']
        
        # Mod 解压目录（脚本所在目录的 mods/ 文件夹）
        script_dir = os.path.dirname(os.path.abspath(__file__))
        self.mods_dir = os.path.join(script_dir, 'mods')
        os.makedirs(self.mods_dir, exist_ok=True)
        
        # 备份目录（脚本所在目录的 backups/ 文件夹）
        self.backup_dir = os.path.join(script_dir, 'backups')
        os.makedirs(self.backup_dir, exist_ok=True)
        
        # 从配置文件读取备份保留数量
        try:
            import json
            config_path = os.path.join(script_dir, 'configs', 'config.json')
            with open(config_path, 'r', encoding='utf-8') as f:
                config = json.load(f)
            self.backup_retention = config.get('ini_backup_retention', 5)
        except:
            self.backup_retention = 5
    
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
    
    def _copy_to_data(self, source_file, mod_name=None):
        """
        复制文件到 Data 目录
        
        Args:
            source_file: 源文件路径
            mod_name: Mod 名称（用于备份时创建子文件夹）
        
        Returns:
            目标文件路径，失败返回 None
        """
        try:
            filename = os.path.basename(source_file)
            target_path = os.path.join(self.data_path, filename)
            
            # 如果目标文件已存在且需要备份，先备份
            if os.path.exists(target_path) and self._should_backup(target_path):
                # 使用文件名的基名作为 mod_name（如果没有提供）
                if not mod_name:
                    mod_name = os.path.splitext(filename)[0]
                self._backup_file(target_path, mod_name)
            
            # 复制文件（保留元数据）
            shutil.copy2(source_file, target_path)
            logger.debug(f"复制文件到 Data 目录: {target_path}")
            return target_path
        except Exception as e:
            logger.error(f"复制文件到 Data 目录失败 {source_file}: {e}")
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
    
    def install_mods_from_folder(self, mod_folder_path):
        """
        从文件夹批量安装 mod
        
        Args:
            mod_folder_path: mod 文件夹路径
        
        Returns:
            安装结果统计字典
        """
        if not os.path.exists(mod_folder_path) or not os.path.isdir(mod_folder_path):
            logger.error(f"Mod 文件夹不存在: {mod_folder_path}")
            return {'success': 0, 'failed': 0, 'mods': []}
        
        logger.info(f"开始扫描 Mod 文件夹: {mod_folder_path}")
        
        # 查找所有 ZIP 文件
        zip_files = []
        for item in os.listdir(mod_folder_path):
            item_path = os.path.join(mod_folder_path, item)
            if os.path.isfile(item_path) and item.lower().endswith('.zip'):
                zip_files.append(item_path)
        
        if not zip_files:
            logger.warning(f"未找到 ZIP 文件: {mod_folder_path}")
            return {'success': 0, 'failed': 0, 'mods': []}
        
        logger.info(f"找到 {len(zip_files)} 个 ZIP 文件")
        
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
                restore = input().strip().lower()
                
                if restore == 'Y':
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
        
        for zip_path in zip_files:
            zip_name = os.path.basename(zip_path)
            logger.info(f"正在安装: {zip_name}")
            
            try:
                # 解压到脚本目录的 mods/ 下的子文件夹
                extracted_files, mod_subfolder = self._extract_zip(zip_path, self.mods_dir)
                
                if not extracted_files:
                    logger.error(f"解压失败: {zip_name}")
                    failed_count += 1
                    continue
                
                logger.debug(f"Mod 解压到子文件夹: {mod_subfolder}")
                
                # 获取 mod 名称（用于备份文件夹命名）
                mod_name = os.path.basename(mod_subfolder)
                
                # 复制文件到 Data 目录
                copied_files = []
                for extracted_file in extracted_files:
                    copied_path = self._copy_to_data(extracted_file, mod_name)
                    if copied_path:
                        copied_files.append(copied_path)
                
                if not copied_files:
                    logger.warning(f"没有文件被复制到 Data 目录: {zip_name}")
                
                # 收集 mod 文件并添加到 INI
                mod_files = self._collect_mod_files(copied_files or extracted_files)
                
                for mod_file in mod_files:
                    if self.ini_manager.add_mod_to_list(mod_file, ini_mode):
                        installed_mods.append(mod_file)
                        logger.info(f"添加 mod 到 INI: {mod_file}")
                        
                        # 注册 mod 到注册表（记录版本号等信息），并标记为已启用
                        if self.mod_registry:
                            version = None  # 由 registry 自动检测
                            self.mod_registry.register_mod(mod_file, zip_path, version, enabled=True)
                
                # 删除原压缩包
                try:
                    os.remove(zip_path)
                    logger.info(f"已删除压缩包: {zip_name}")
                except Exception as e:
                    logger.warning(f"删除压缩包失败 {zip_name}: {e}")
                
                success_count += 1
                logger.info(f"成功安装: {zip_name}")
                
            except Exception as e:
                logger.error(f"安装 mod 失败 {zip_name}: {e}")
                failed_count += 1
        
        result = {
            'success': success_count,
            'failed': failed_count,
            'mods': installed_mods
        }
        
        logger.info(f"安装完成: 成功 {success_count} 个, 失败 {failed_count} 个")
        return result

