import threading
import time
import os
import json
import sys

from msvcrt import getwch

from calculate_string_length import Calc_String_Width, Cut_And_Pad_String


class ReaderCLI:
    def __init__(self) -> None:
        self.HISTORY_FILE = os.path.join(os.path.expanduser('~'), 'LuisNovelReader\history.json')
        self.HEADER_FOOTER_HEIGHT = 8  # 标题和状态栏占用的行数
        os.system('colors')  # 启用 Windows 终端颜色支持
        os.system('title Novel Reader CLI')
        os.system('cls')
        self.LoopFlag = True
        self.Terminal_Width, self.Terminal_Height = os.get_terminal_size()
        self.KeyQueue = []
        self._read_config()
        self.CurrentDirFiles = []
        self.CurrentDirDirs = []
        self.CurrentDirDisplayContent = []
        self.CursorPos = 0
        self.CurrentFilePath = ''
        self.CurrentFile = None
        self.CurrentFileDisplayContent = []
        self.CurrentFilePoss = [0]
        self.CurrentFileEncoding = ''
        self.CurrentPage = ''
        # 绘制相关变量
        self.CurrentDirDisplayOffset = 0
        self.CDDSLens = 0
        self.CDFSLens = 0
        self.LeftWidth = (self.Terminal_Width - 3) // 3
        self.RightWidth = self.Terminal_Width - 3 - self.LeftWidth - 1  # 1 for separator
        self.LeftTitle = Cut_And_Pad_String('File Browser ', self.LeftWidth-3 - 1, cut_align='right', pad_align='right', pad_char=' ')
        self.RightTitle = Cut_And_Pad_String(f'File Viewer ', self.RightWidth-3 - 1, cut_align='left', pad_align='right', pad_char=' ')
        
    def _read_config(self) -> None:
        try:
            with open('config.json', 'r', encoding='utf-8') as f:
                config = json.load(f)
            self.CurrentDir = config.get('last_directory', os.getcwd())
        except (FileNotFoundError, json.JSONDecodeError):
            self.CurrentDir = os.getcwd()

    def _listen_terminal_size(self) -> None:
        while self.LoopFlag:
            try:
                a, b = os.get_terminal_size()
            except:
                time.sleep(0.5)
                continue
            if a != self.Terminal_Width or b != self.Terminal_Height:
                self.Terminal_Width, self.Terminal_Height = a, b
                self.LeftWidth = (self.Terminal_Width - 3) // 3
                self.RightWidth = self.Terminal_Width - 3 - self.LeftWidth - 1  # 1 for separator
                self.LeftTitle = Cut_And_Pad_String('File Browser ', self.LeftWidth-3 - 1, cut_align='right', pad_align='right', pad_char=' ')
                if self.CurrentFilePath:
                    self.RightTitle = Cut_And_Pad_String(f'{self.CurrentFilePath} ', self.RightWidth-3 - 1, cut_align='left', pad_align='right', pad_char=' ')
                else:
                    self.RightTitle = Cut_And_Pad_String(f'File Viewer ', self.RightWidth-3 - 1, cut_align='left', pad_align='right', pad_char=' ')
                self._load_directory(self.CurrentDir)
                if self.CurrentFile:
                    if len(self.CurrentFilePoss) > 1:
                        self.CurrentFilePoss = self.CurrentFilePoss[:-1]
                    self._try_update_file_content()
                os.system('cls')
                self.draw()
            time.sleep(0.5)  # 增加检查间隔，减少CPU占用

    def _listen_keyboard(self) -> None:
        while self.LoopFlag:
            key = getwch()
            if key == '\x03':  # Ctrl+C
                key = 'CTRLC'
            elif key == '\r':  # Enter
                key = 'ENTER'
            elif key == '\x1b':  # Escape
                key = 'ESC'
            elif key == '\t':  # Tab
                key = 'TAB'
            elif key == '\xe0':  # Special keys (arrows, f keys, ins, del, etc.)
                key = getwch()
                if key == 'H':
                    key = 'UP'
                elif key == 'P':
                    key = 'DOWN'
                elif key == 'K':
                    key = 'LEFT'
                elif key == 'M':
                    key = 'RIGHT'
                else:
                    continue  # 使用 continue 而不是 return
            if not self.KeyQueue:
                self.KeyQueue.append(key)
            elif key != self.KeyQueue[-1]:
                self.KeyQueue = [key]
            #time.sleep(0.1)  # 设置最小间隔

    def draw(self) -> None:

        ### 左侧为文件列表区域，右侧为文件观看区域 ###
        # 使用缓冲区收集所有输出内容
        buffer = '┌' + '─' * self.LeftWidth + '┬' + '─' * self.RightWidth + '┐\n'
        
        # 使用 Cut_And_Pad_String 处理标题行
        if self.CurrentPage == 'file_select':
            buffer += f"│ \033[32m●\033[0m {self.LeftTitle}"
        else:
            buffer += f"│    {self.LeftTitle}"
        if self.CurrentPage == 'file_view':
            buffer += f"│ \033[32m●\033[0m {self.RightTitle}│\n"
        else:
            buffer += f"│    {self.RightTitle}│\n"
        buffer += '├' + '─' * self.LeftWidth + '┼' + '─' * self.RightWidth + '┤\n'
        
        total_items = self.CDDSLens + self.CDFSLens
        cfdcLen_ = len(self.CurrentFileDisplayContent)
        for i in range(max(self.Terminal_Height - self.HEADER_FOOTER_HEIGHT, 1)):  # -n for header and footer
            if i < total_items:
                if i == self.CursorPos:
                    line = f" > \033[7m{self.CurrentDirDisplayContent[i]}\033[0m"
                else:
                    line = f"   {self.CurrentDirDisplayContent[i]}"
            else:
                line = ' ' * self.LeftWidth
            # 使用 Cut_And_Pad_String 处理右侧区域
            if i < cfdcLen_:
                right_content = self.CurrentFileDisplayContent[i]
                #right_content = Cut_And_Pad_String(self.CurrentFileDisplayContent[i], right_width, cut_align='right', pad_align='right', pad_char=' ')
            else:
                right_content = ' ' * (self.RightWidth - 1)
                #right_content = ''
            buffer += f"│{line}│ {right_content}│\n"
        
        buffer += '├' + '─' * self.LeftWidth + '┴' + '─' * self.RightWidth + '┤\n'
        buffer += '│' + Cut_And_Pad_String(f'当前目录: {self.CurrentDir}', self.Terminal_Width-3, cut_align='right', pad_align='right', pad_char=' ') + '│\n'
        buffer += '│' + Cut_And_Pad_String(f'文件数: {self.CDFSLens} | 目录数: {self.CDDSLens} | 文件编码: {self.CurrentFileEncoding}', self.Terminal_Width-3, cut_align='right', pad_align='right', pad_char=' ') + '│\n'
        buffer += '│' + Cut_And_Pad_String(f'↑↓移动  Enter/→ 进入目录/打开文件  Tab 切换页面  Esc/Ctrl+C 退出', self.Terminal_Width-3, cut_align='right', pad_align='right', pad_char=' ') + '│\n'
        buffer += '└' + '─' * self.LeftWidth + '─' + '─' * self.RightWidth + '┘\n'

        # 使用 ANSI 转义序列而不是 cls，更快且无闪烁
        # \033[2J 清屏，\033[H 移动光标到左上角
        sys.stdout.write('\033[H\033[J\033[?25l' + buffer[:-1])  # 去掉最后一个多余的换行
        sys.stdout.flush()

    def _update_directory_display_content(self) -> None:
        self.CurrentDirDisplayContent = []
        for i in range(self.CurrentDirDisplayOffset, min(self.Terminal_Height - self.HEADER_FOOTER_HEIGHT, self.CDDSLens + self.CDFSLens) + self.CurrentDirDisplayOffset):  # -n for header and footer
            if i < self.CDDSLens:
                item = self.CurrentDirDirs[i]
                prefix = " [DIR] "
            elif i - len(self.CurrentDirDirs) < len(self.CurrentDirFiles):
                item = self.CurrentDirFiles[i - len(self.CurrentDirDirs)]
                prefix = "       "
            line = f"{prefix}{item}"
            line = Cut_And_Pad_String(line, self.LeftWidth-3, cut_align='right', pad_align='right', pad_char=' ')
            line = Cut_And_Pad_String(line, self.LeftWidth-3, cut_align='right', pad_align='right', pad_char=' ')
            self.CurrentDirDisplayContent.append(line)

    def _load_directory(self, path) -> None:
        """异步加载目录内容"""
        try:
            items = os.listdir(path)
            dirs = [d for d in items if os.path.isdir(os.path.join(path, d))]
            files = [f for f in items if os.path.isfile(os.path.join(path, f))]
            self.CurrentDirDirs = ['..'] + dirs
            self.CurrentDirFiles = files
        except PermissionError:
            self.CurrentDirDirs = ['..']
            self.CurrentDirFiles = []
        self.CDDSLens = len(self.CurrentDirDirs)
        self.CDFSLens = len(self.CurrentDirFiles)
        self.CurrentDirDisplayOffset = 0
        self._update_directory_display_content()

    def _get_file_pos_history(self) -> None:
        if not os.path.exists(os.path.dirname(self.HISTORY_FILE)):
            os.makedirs(os.path.dirname(self.HISTORY_FILE))
        try:
            with open(self.HISTORY_FILE, 'r', encoding='utf-8') as f:
                history = json.load(f)
            self.CurrentFilePoss = history.get(self.CurrentFilePath, [0])
            if not self.CurrentFilePoss:
                self.CurrentFilePoss = [0]
        except:
            self.CurrentFilePoss = [0]

    def _update_file_pos_history(self) -> None:
        if not os.path.exists(os.path.dirname(self.HISTORY_FILE)):
            os.makedirs(os.path.dirname(self.HISTORY_FILE))
        try:
            with open(self.HISTORY_FILE, 'r', encoding='utf-8') as f:
                try:
                    history = json.load(f)
                except json.JSONDecodeError:
                    history = {}
        except FileNotFoundError:
            history = {}
        history[self.CurrentFilePath] = self.CurrentFilePoss[:-1]
        with open(self.HISTORY_FILE, 'w', encoding='utf-8') as f:
            json.dump(history, f, ensure_ascii=False, indent=4)

    def _update_next_file_content(self) -> None:
        self.CurrentFile.seek(self.CurrentFilePoss[-1])
        self.CurrentFileDisplayContent = []
        # 填充显示的内容
        if self.CurrentFile:
            for _ in range(self.Terminal_Height - self.HEADER_FOOTER_HEIGHT):  # -n for header and footer
                __ = ''
                while Calc_String_Width(__) < self.RightWidth - 1:
                    while True:
                        char = self.CurrentFile.read(1)
                        if char == '\t':
                            char = '    '
                        elif not char:
                            if len(self.CurrentFilePoss) > 1 and self.CurrentFilePoss[-1] != self.CurrentFilePoss[-2]:
                                self.CurrentFilePoss.append(self.CurrentFilePoss[-1])
                            raise EOFError
                        elif char != '\r':
                            break
                    if char == '\n':
                        break
                    __ += char
                if Calc_String_Width(__) > self.RightWidth - 1:
                    self.CurrentFile.seek(self.CurrentFile.tell() - len(__[-1].encode(self.CurrentFileEncoding)))
                    __ = __[:-1]
                __ = Cut_And_Pad_String(__, self.RightWidth - 1, cut_align='right', pad_align='right', pad_char=' ')
                self.CurrentFileDisplayContent.append(__)
            self.CurrentFilePoss.append(self.CurrentFile.tell())

    def _try_open_file(self, start:str) -> int:
        if start == 'gbk':
            return 2
        try:
            if start != '':
                # 抛出异常以尝试其他编码
                raise Exception("Force try other encodings")
            self.CurrentFile = open(self.CurrentFilePath, 'r', encoding='utf-8-sig')
            self.CurrentFileEncoding = 'utf-8-sig'
        except:
            try:
                if start != 'utf-8-sig':
                    raise Exception("Force try other encodings")
                self.CurrentFile = open(self.CurrentFilePath, 'r', encoding='utf-8')
                self.CurrentFileEncoding = 'utf-8'
            except:
                try:
                    if start != 'utf-8':
                        raise Exception("Force try other encodings")
                    self.CurrentFile = open(self.CurrentFilePath, 'r', encoding='gbk')
                    self.CurrentFileEncoding = 'gbk'
                #except:
                    #try:
                    #    if start != 'gbk':
                    #        raise Exception("Force try other encodings")
                    #    self.CurrentFile = open(self.CurrentFilePath, 'r', encoding='latin-1')
                    #    self.CurrentFileEncoding = 'latin-1'
                except FileNotFoundError:
                    return -1
                except:
                    return 0
        return 1
    
    def _try_update_file_content(self) -> bool:
        try:
            self._update_next_file_content()
            return 1
        except EOFError:
            self.CurrentFileDisplayContent.append('\033[31m' + Cut_And_Pad_String(' <已到达文件末尾>', self.RightWidth - 1, cut_align='right', pad_align='right', pad_char=' ') + '\033[0m')
            return 1
        except:
            status_ = self._try_open_file(self.CurrentFileEncoding)
            if status_ == -1:
                self.CurrentFileDisplayContent = ['\033[31m' + Cut_And_Pad_String(' <无法打开文件>', self.RightWidth - 1, cut_align='right', pad_align='right', pad_char=' ') + '\033[0m']
                self.CurrentFile = None
                self.CurrentFileEncoding = ''
                return 1
            elif status_ in [0, 2]:
                # 如果仍然失败，尝试用 latin-1 打开（能处理所有字节）
                self.CurrentFileDisplayContent = ['\033[31m' + Cut_And_Pad_String(' <不支持的编码格式>', self.RightWidth - 1, cut_align='right', pad_align='right', pad_char=' ') + '\033[0m']
                self.CurrentFile = None
                self.CurrentFileEncoding = ''
                return 1
        return 0


    def run(self) -> None:
        threading.Thread(target=self._listen_terminal_size, daemon=True).start()
        threading.Thread(target=self._listen_keyboard, daemon=True).start()
        # 初始化文件列表
        self._load_directory(self.CurrentDir)
        while self.LoopFlag:
            self.select_file_page()
        os.system('cls')

    def select_file_page(self) -> None:
        self.CurrentPage = 'file_select'
        self.draw()  # 首次绘制清屏
        while self.LoopFlag:
            if self.KeyQueue:
                key = self.KeyQueue.pop(0)
                if key in ['ESC', 'CTRLC']:
                    self.LoopFlag = False
                    break
                elif key in ['UP']:
                    if self.CursorPos == 0 and self.CurrentDirDisplayOffset > 0:
                        self.CurrentDirDisplayOffset -= 1
                        self._update_directory_display_content()
                    else:
                        self.CursorPos -= 1
                    if self.CursorPos == -1:
                        self.CurrentDirDisplayOffset = max(0, self.CDDSLens + self.CDFSLens - (self.Terminal_Height - self.HEADER_FOOTER_HEIGHT))
                        self.CursorPos = min(self.Terminal_Height - self.HEADER_FOOTER_HEIGHT -1, self.CDDSLens + self.CDFSLens -1)
                        self._update_directory_display_content()
                    self.draw()
                elif key in ['DOWN']:
                    if self.CursorPos == self.Terminal_Height - self.HEADER_FOOTER_HEIGHT -1 and self.CursorPos + self.CurrentDirDisplayOffset < self.CDDSLens + self.CDFSLens -1:
                        self.CurrentDirDisplayOffset += 1
                        self._update_directory_display_content()
                    else:
                        self.CursorPos += 1
                    if self.CursorPos == min(self.Terminal_Height - self.HEADER_FOOTER_HEIGHT, self.CDDSLens + self.CDFSLens):
                        self.CurrentDirDisplayOffset = 0
                        self.CursorPos = 0
                        self._update_directory_display_content()
                    self.draw()
                elif key in ['ENTER', 'RIGHT']:
                    real_cursor = self.CursorPos + self.CurrentDirDisplayOffset
                    if real_cursor < len(self.CurrentDirDirs):
                        selected_dir = self.CurrentDirDirs[real_cursor]
                        if selected_dir == '..':
                            new_dir = os.path.dirname(self.CurrentDir)
                        else:
                            new_dir = os.path.join(self.CurrentDir, selected_dir)
                        
                        if os.path.exists(new_dir):
                            self.CurrentDir = new_dir
                            self.CursorPos = 0
                            self._load_directory(self.CurrentDir)
                    else:
                        selected_file = self.CurrentDirFiles[real_cursor - len(self.CurrentDirDirs)]
                        self.CurrentFilePath = os.path.join(self.CurrentDir, selected_file)
                        self.RightTitle = Cut_And_Pad_String(f'{self.CurrentFilePath} ', self.RightWidth-3 - 1, cut_align='left', pad_align='right', pad_char=' ')
                        status_ = self._try_open_file('')
                        if status_ == -1:
                            self.CurrentFileDisplayContent = ['\033[31m' + Cut_And_Pad_String(' <无法打开文件>', self.RightWidth - 1, cut_align='right', pad_align='right', pad_char=' ') + '\033[0m']
                            self.CurrentFile = None
                            self.CurrentFileEncoding = ''
                        elif status_ == 0:
                            # 如果仍然失败，尝试用 latin-1 打开（能处理所有字节）
                            self.CurrentFileDisplayContent = ['\033[31m' + Cut_And_Pad_String(' <不支持的编码格式>', self.RightWidth - 1, cut_align='right', pad_align='right', pad_char=' ') + '\033[0m']
                            self.CurrentFile = None
                            self.CurrentFileEncoding = ''
                        self._get_file_pos_history()
                        while True:
                            if self._try_update_file_content():
                                break
                    self.draw()  # 目录切换时清屏
                elif key in ['TAB']:
                    self.read_file_page()  # 切换到文件阅读页面
                    self.CurrentPage = 'file_select'
                    self.draw()  # 返回文件选择页面时重绘
            else:
                time.sleep(0.01)  # 添加短暂延迟，避免CPU空转

    def read_file_page(self) -> None:
        self.CurrentPage = 'file_view'
        self.draw()  # 重绘
        while self.LoopFlag:
            if self.KeyQueue:
                key = self.KeyQueue.pop(0)
                if key in ['ESC', 'CTRLC']:
                    self.LoopFlag = False
                    self._update_file_pos_history()
                    break
                elif key in ['LEFT', 'TAB']:
                    self._update_file_pos_history()
                    break  # 返回文件选择页面
                elif key in ['UP']:
                    if len(self.CurrentFilePoss) > 2:
                        self.CurrentFilePoss = self.CurrentFilePoss[:-2]
                    else:
                        self.CurrentFilePoss = [0]
                    while True:
                        if self._try_update_file_content():
                            break
                    self.draw()
                elif key in ['DOWN']:
                    while True:
                        if self._try_update_file_content():
                            break
                    self.draw()
            else:
                time.sleep(0.01)  # 添加短暂延迟，避免CPU空转

if __name__ == "__main__":
    cli = ReaderCLI()
    cli.run()