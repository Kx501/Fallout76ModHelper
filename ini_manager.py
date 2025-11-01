"""
INI 配置管理模块 - 管理 Fallout76Custom.ini 文件
"""
import os
import configparser
import shutil
import glob
from datetime import datetime
from logger import get_logger

logger = get_logger()


class IniManager:
    """INI 文件管理器"""
    
    def __init__(self, config_dir, backup_retention=5):
        """
        初始化 INI 管理器
        
        Args:
            config_dir: 配置目录路径（Documents\My Games\Fallout 76）
            backup_retention: 保留的备份数量（默认5个）
        """
        self.config_dir = config_dir
        self.ini_path = os.path.join(config_dir, 'Fallout76Custom.ini')
        self.parser = configparser.ConfigParser()
        self.parser.optionxform = str  # 保持键名大小写
        
        # 备份目录（脚本所在目录的 backups/ 文件夹）
        script_dir = os.path.dirname(os.path.abspath(__file__))
        self.backup_dir = os.path.join(script_dir, 'backups')
        os.makedirs(self.backup_dir, exist_ok=True)
        
        self.backup_retention = backup_retention
    
    def _ensure_ini_exists(self):
        """确保 INI 文件存在，不存在则创建"""
        if not os.path.exists(self.ini_path):
            try:
                # 创建默认结构
                os.makedirs(os.path.dirname(self.ini_path), exist_ok=True)
                with open(self.ini_path, 'w', encoding='utf-8') as f:
                    f.write("[Archive]\n")
                logger.info(f"创建 INI 文件: {self.ini_path}")
            except Exception as e:
                logger.error(f"创建 INI 文件失败: {e}")
                return False
        return True
    
    def _read_ini(self):
        """读取 INI 文件"""
        if not self._ensure_ini_exists():
            return False
        
        try:
            # 设置编码为 utf-8（带 BOM 的 INI 文件）
            with open(self.ini_path, 'r', encoding='utf-8-sig') as f:
                content = f.read()
            self.parser.read_string(content)
            logger.debug(f"成功读取 INI 文件: {self.ini_path}")
            return True
        except Exception as e:
            logger.error(f"读取 INI 文件失败: {e}")
            return False
    
    def _backup_ini(self):
        """
        备份 INI 文件到脚本目录的 backups/ 文件夹
        
        Returns:
            备份文件路径，失败返回 None
        """
        if not os.path.exists(self.ini_path):
            return None
        
        try:
            # 生成备份文件名（包含时间戳）
            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
            backup_filename = f"Fallout76Custom_{timestamp}.ini"
            backup_path = os.path.join(self.backup_dir, backup_filename)
            
            # 复制文件
            shutil.copy2(self.ini_path, backup_path)
            logger.info(f"备份 INI 文件: {backup_path}")
            
            # 清理旧备份
            self._cleanup_old_backups()
            
            return backup_path
        except Exception as e:
            logger.warning(f"备份 INI 文件失败: {e}")
            return None
    
    def _cleanup_old_backups(self):
        """清理旧的备份文件，只保留最近的 N 个"""
        try:
            # 获取所有备份文件
            backup_pattern = os.path.join(self.backup_dir, 'Fallout76Custom_*.ini')
            backups = glob.glob(backup_pattern)
            
            if len(backups) <= self.backup_retention:
                return
            
            # 按修改时间排序（最新的在前）
            backups.sort(key=os.path.getmtime, reverse=True)
            
            # 删除多余的备份
            to_remove = backups[self.backup_retention:]
            for backup in to_remove:
                try:
                    os.remove(backup)
                    logger.debug(f"删除旧备份: {backup}")
                except Exception as e:
                    logger.warning(f"删除旧备份失败 {backup}: {e}")
        
        except Exception as e:
            logger.warning(f"清理旧备份失败: {e}")
    
    def _write_ini(self):
        """写入 INI 文件（写入前会先备份）"""
        # 写入前先备份
        if os.path.exists(self.ini_path):
            self._backup_ini()
        
        try:
            with open(self.ini_path, 'w', encoding='utf-8') as f:
                self.parser.write(f)
            logger.debug(f"成功写入 INI 文件: {self.ini_path}")
            return True
        except Exception as e:
            logger.error(f"写入 INI 文件失败: {e}")
            return False
    
    def add_mod_to_list(self, mod_name, list_type='sResourceArchive2List'):
        """
        添加 mod 到指定列表
        
        Args:
            mod_name: mod 文件名（如 "ModName.ba2"）
            list_type: 列表类型（sResourceArchive2List 或 sResourceIndexFileList）
        
        Returns:
            是否成功添加
        """
        if not self._read_ini():
            return False
        
        # 确保 [Archive] 节存在
        if not self.parser.has_section('Archive'):
            self.parser.add_section('Archive')
        
        # 获取当前列表值
        current_value = self.parser.get('Archive', list_type, fallback='').strip()
        
        # 检查 mod 是否已存在
        mod_list = [m.strip() for m in current_value.split(',') if m.strip()]
        if mod_name in mod_list:
            logger.debug(f"Mod {mod_name} 已存在于 {list_type}")
            return True
        
        # 添加 mod
        if current_value:
            new_value = f"{current_value}, {mod_name}"
        else:
            new_value = mod_name
        
        self.parser.set('Archive', list_type, new_value)
        
        if self._write_ini():
            logger.info(f"成功添加 mod {mod_name} 到 {list_type}")
            return True
        else:
            logger.error(f"添加 mod {mod_name} 到 {list_type} 失败")
            return False
    
    def remove_mod_from_list(self, mod_name, list_type='sResourceArchive2List'):
        """
        从列表中移除 mod
        
        Args:
            mod_name: mod 文件名
            list_type: 列表类型
        
        Returns:
            是否成功移除
        """
        if not self._read_ini():
            return False
        
        if not self.parser.has_section('Archive'):
            return True
        
        current_value = self.parser.get('Archive', list_type, fallback='').strip()
        if not current_value:
            return True
        
        # 移除 mod
        mod_list = [m.strip() for m in current_value.split(',') if m.strip()]
        if mod_name not in mod_list:
            return True
        
        mod_list.remove(mod_name)
        new_value = ', '.join(mod_list)
        
        if new_value:
            self.parser.set('Archive', list_type, new_value)
        else:
            self.parser.remove_option('Archive', list_type)
        
        if self._write_ini():
            logger.info(f"成功从 {list_type} 移除 mod {mod_name}")
            return True
        else:
            logger.error(f"从 {list_type} 移除 mod {mod_name} 失败")
            return False
    
    def get_mod_list(self, list_type='sResourceArchive2List'):
        """
        获取当前列表中的所有 mod
        
        Args:
            list_type: 列表类型
        
        Returns:
            mod 列表
        """
        if not self._read_ini():
            return []
        
        if not self.parser.has_section('Archive'):
            return []
        
        current_value = self.parser.get('Archive', list_type, fallback='').strip()
        if not current_value:
            return []
        
        return [m.strip() for m in current_value.split(',') if m.strip()]
    
    def detect_current_mode(self):
        """
        检测当前 INI 文件中使用的是哪个模式
        
        Returns:
            当前使用的列表类型，如果两个都有则返回包含mod最多的，如果都没有返回 None
        """
        if not self._read_ini():
            return None
        
        if not self.parser.has_section('Archive'):
            return None
        
        list2 = self.get_mod_list('sResourceArchive2List')
        index = self.get_mod_list('sResourceIndexFileList')
        
        # 如果两个列表都有 mod，返回包含更多 mod 的
        if list2 and index:
            return 'sResourceArchive2List' if len(list2) >= len(index) else 'sResourceIndexFileList'
        elif list2:
            return 'sResourceArchive2List'
        elif index:
            return 'sResourceIndexFileList'
        else:
            return None
    
    def sync_mode(self, target_mode):
        """
        同步 INI 文件中的模式到目标模式
        
        如果当前模式与目标模式不一致，将所有 mod 从旧列表迁移到新列表
        
        Args:
            target_mode: 目标模式（sResourceArchive2List 或 sResourceIndexFileList）
        
        Returns:
            是否成功同步，如果无需同步返回 True
        """
        if not self._read_ini():
            return False
        
        current_mode = self.detect_current_mode()
        
        # 如果当前模式就是目标模式，无需同步
        if current_mode == target_mode:
            logger.debug(f"INI 模式已与配置一致: {target_mode}")
            return True
        
        # 确定源列表和目标列表
        if target_mode == 'sResourceArchive2List':
            source_mode = 'sResourceIndexFileList'
            target_list_name = 'sResourceArchive2List'
            source_list_name = 'sResourceIndexFileList'
        else:
            source_mode = 'sResourceArchive2List'
            target_list_name = 'sResourceIndexFileList'
            source_list_name = 'sResourceArchive2List'
        
        # 获取需要迁移的 mod 列表
        mods_to_migrate = self.get_mod_list(source_list_name)
        target_mods = self.get_mod_list(target_list_name)
        
        if not mods_to_migrate:
            logger.debug(f"没有需要迁移的 mod，直接设置目标模式: {target_mode}")
            # 即使没有需要迁移的，我们也确保目标模式存在（为空列表）
            if not self.parser.has_section('Archive'):
                self.parser.add_section('Archive')
            if not self.parser.has_option('Archive', target_list_name):
                self.parser.set('Archive', target_list_name, '')
            return self._write_ini()
        
        # 合并 mod 列表（避免重复）
        all_mods = set(target_mods) | set(mods_to_migrate)
        merged_mods = list(all_mods)
        
        # 更新目标列表
        if not self.parser.has_section('Archive'):
            self.parser.add_section('Archive')
        
        if merged_mods:
            new_value = ', '.join(sorted(merged_mods))
            self.parser.set('Archive', target_list_name, new_value)
        else:
            self.parser.set('Archive', target_list_name, '')
        
        # 清空源列表
        self.parser.remove_option('Archive', source_list_name)
        
        if self._write_ini():
            logger.info(f"成功同步 INI 模式: {current_mode} -> {target_mode} (迁移了 {len(mods_to_migrate)} 个 mod)")
            return True
        else:
            logger.error(f"同步 INI 模式失败: {current_mode} -> {target_mode}")
            return False

