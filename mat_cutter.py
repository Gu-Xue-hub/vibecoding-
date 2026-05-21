import numpy as np
import scipy.io as sio
import matplotlib.pyplot as plt
from matplotlib.widgets import Button, RadioButtons, Slider
from matplotlib.patches import Rectangle
import matplotlib

matplotlib.rcParams['font.sans-serif'] = ['DejaVu Sans', 'SimHei', 'Heiti SC']
matplotlib.rcParams['axes.unicode_minus'] = False

class MatDataViewer:
    def __init__(self):
        self.data_list = []
        self.data_names = []
        self.current_data_idx = 0
        self.data = None
        self.bands = None
        self.rows = None
        self.cols = None
        self.current_display = None
        self.r_band = 0
        self.g_band = 1
        self.b_band = 2
        self.display_mode = 'single'
        self.single_band = 0
        
        self.fig, self.ax = plt.subplots(figsize=(14, 9))
        plt.subplots_adjust(left=0.28, bottom=0.25, right=0.72)
        
        self.rect = None
        self.start_x = None
        self.start_y = None
        self.drawing = False
        
        self.crop_x0 = None
        self.crop_y0 = None
        self.crop_width = None
        self.crop_height = None
        
        self.setup_ui()
        self.setup_events()
        
    def setup_ui(self):
        axcolor = 'lightgoldenrodyellow'
        
        self.ax_single_slider = plt.axes([0.28, 0.15, 0.44, 0.03], facecolor=axcolor)
        self.single_slider = Slider(self.ax_single_slider, 'Band', 0, 1, valinit=0, valstep=1)
        
        self.ax_r_slider = plt.axes([0.28, 0.10, 0.44, 0.03], facecolor=axcolor)
        self.r_slider = Slider(self.ax_r_slider, 'R Band', 0, 1, valinit=0, valstep=1)
        
        self.ax_g_slider = plt.axes([0.28, 0.05, 0.44, 0.03], facecolor=axcolor)
        self.g_slider = Slider(self.ax_g_slider, 'G Band', 0, 1, valinit=1, valstep=1)
        
        self.ax_b_slider = plt.axes([0.28, 0.0, 0.44, 0.03], facecolor=axcolor)
        self.b_slider = Slider(self.ax_b_slider, 'B Band', 0, 1, valinit=2, valstep=1)
        
        self.ax_radio = plt.axes([0.02, 0.5, 0.18, 0.2], facecolor=axcolor)
        self.radio = RadioButtons(self.ax_radio, ('Single', 'RGB'), active=0)
        
        self.ax_load = plt.axes([0.02, 0.35, 0.18, 0.075])
        self.btn_load = Button(self.ax_load, 'Load MAT')
        
        self.ax_add = plt.axes([0.02, 0.25, 0.18, 0.075])
        self.btn_add = Button(self.ax_add, 'Add MAT')
        
        self.ax_save = plt.axes([0.02, 0.15, 0.18, 0.075])
        self.btn_save = Button(self.ax_save, 'Save Crop')
        
        self.ax_save_all = plt.axes([0.02, 0.05, 0.18, 0.075])
        self.btn_save_all = Button(self.ax_save_all, 'Save All')
        
        self.ax_clear = plt.axes([0.82, 0.05, 0.16, 0.075])
        self.btn_clear = Button(self.ax_clear, 'Clear')
        
        self.ax_verify = plt.axes([0.82, 0.15, 0.16, 0.075])
        self.btn_verify = Button(self.ax_verify, 'Verify Crop')
        
        self.ax_info = plt.axes([0.02, 0.78, 0.18, 0.18])
        self.ax_info.set_axis_off()
        self.info_text = self.ax_info.text(0, 0.95, 'Waiting for data...', fontsize=9)
        
        self.ax_crop_info = plt.axes([0.82, 0.78, 0.16, 0.18])
        self.ax_crop_info.set_axis_off()
        self.crop_info_text = self.ax_crop_info.text(0, 0.95, 'Crop Info:\n', fontsize=9)
        
        self.ax_data_sel = plt.axes([0.82, 0.25, 0.16, 0.4], facecolor=axcolor)
        self.data_sel_text = self.ax_data_sel.text(0, 0.95, 'Loaded Data:\n', fontsize=9)
        self.ax_data_sel.set_axis_off()
        
        self.sliders = [self.single_slider, self.r_slider, self.g_slider, self.b_slider]
        self.hide_sliders()
        
    def setup_events(self):
        self.btn_load.on_clicked(self.load_mat)
        self.btn_add.on_clicked(self.add_mat)
        self.btn_save.on_clicked(self.save_crop)
        self.btn_save_all.on_clicked(self.save_all_crops)
        self.btn_clear.on_clicked(self.clear_rect)
        self.btn_verify.on_clicked(self.verify_crop)
        self.radio.on_clicked(self.change_display_mode)
        self.single_slider.on_changed(self.update_single_band)
        self.r_slider.on_changed(self.update_rgb_bands)
        self.g_slider.on_changed(self.update_rgb_bands)
        self.b_slider.on_changed(self.update_rgb_bands)
        
        self.cid_press = self.fig.canvas.mpl_connect('button_press_event', self.on_press)
        self.cid_release = self.fig.canvas.mpl_connect('button_release_event', self.on_release)
        self.cid_motion = self.fig.canvas.mpl_connect('motion_notify_event', self.on_motion)
        self.cid_click = self.fig.canvas.mpl_connect('button_press_event', self.on_data_list_click)
        
    def hide_sliders(self):
        for slider in self.sliders:
            slider.ax.set_visible(False)
            
    def show_sliders(self, slider_indices):
        self.hide_sliders()
        for i in slider_indices:
            self.sliders[i].ax.set_visible(True)
            
    def update_slider_range(self, slider, bands):
        slider.valmin = 0
        slider.valmax = max(0, bands - 1)
        slider.ax.set_xlim(0, max(1, bands - 1))
        slider.ax.figure.canvas.draw()
            
    def load_mat(self, event):
        import tkinter as tk
        from tkinter import filedialog
        
        root = tk.Tk()
        root.withdraw()
        file_path = filedialog.askopenfilename(filetypes=[('MAT files', '*.mat')])
        
        if not file_path:
            return
            
        self.data_list = []
        self.data_names = []
        self.current_data_idx = 0
        self.add_mat_data(file_path)
            
    def add_mat(self, event):
        import tkinter as tk
        from tkinter import filedialog
        
        root = tk.Tk()
        root.withdraw()
        file_path = filedialog.askopenfilename(filetypes=[('MAT files', '*.mat')])
        
        if not file_path:
            return
            
        self.add_mat_data(file_path)
        
    def add_mat_data(self, file_path):
        try:
            mat_contents = sio.loadmat(file_path)
            data_keys = [k for k in mat_contents.keys() if not k.startswith('_')]
            
            if len(data_keys) == 0:
                self.info_text.set_text('No data found')
                return
                
            data_key = data_keys[0]
            data = mat_contents[data_key]
            
            if len(data.shape) == 3:
                rows, cols, bands = data.shape
            elif len(data.shape) == 2:
                data = data[..., np.newaxis]
                rows, cols, bands = data.shape
            else:
                self.info_text.set_text('Unsupported dimensions')
                return
                
            self.data_list.append(data)
            self.data_names.append(file_path.split('/')[-1])
            
            self.current_data_idx = len(self.data_list) - 1
            self.data = self.data_list[self.current_data_idx]
            self.rows = rows
            self.cols = cols
            self.bands = bands
            
            self.info_text.set_text(f'Data: {self.data_names[-1]}\nRows: {self.rows}\nCols: {self.cols}\nBands: {self.bands}')
            
            self.update_data_list_display()
            
            self.update_slider_range(self.single_slider, self.bands)
            self.update_slider_range(self.r_slider, self.bands)
            self.update_slider_range(self.g_slider, self.bands)
            self.update_slider_range(self.b_slider, self.bands)
            
            self.single_band = min(self.single_band, self.bands - 1)
            self.r_band = min(self.r_band, self.bands - 1)
            self.g_band = min(self.g_band, self.bands - 1)
            self.b_band = min(self.b_band, self.bands - 1)
            
            self.single_slider.set_val(self.single_band)
            self.r_slider.set_val(self.r_band)
            self.g_slider.set_val(self.g_band)
            self.b_slider.set_val(self.b_band)
            
            if self.display_mode == 'single':
                self.show_sliders([0])
            else:
                self.show_sliders([1, 2, 3])
            
            self.update_display()
            
        except Exception as e:
            self.info_text.set_text(f'Load failed:\n{str(e)}')
            
    def update_data_list_display(self):
        text = 'Loaded Data:\n'
        for i, name in enumerate(self.data_names):
            marker = '-> ' if i == self.current_data_idx else '   '
            text += f'{marker}{name}\n'
        self.data_sel_text.set_text(text)
        self.fig.canvas.draw()
        
    def on_data_list_click(self, event):
        if event.inaxes == self.ax_data_sel and len(self.data_list) > 1:
            y_pos = event.ydata
            if y_pos is not None:
                idx = int((0.95 - y_pos) * len(self.data_list) / 0.7)
                if 0 <= idx < len(self.data_list):
                    self.switch_data(idx)
                    
    def switch_data(self, idx):
        if idx < 0 or idx >= len(self.data_list):
            return
            
        self.current_data_idx = idx
        self.data = self.data_list[idx]
        self.rows, self.cols, self.bands = self.data.shape
        
        self.info_text.set_text(f'Data: {self.data_names[idx]}\nRows: {self.rows}\nCols: {self.cols}\nBands: {self.bands}')
        
        self.update_slider_range(self.single_slider, self.bands)
        self.update_slider_range(self.r_slider, self.bands)
        self.update_slider_range(self.g_slider, self.bands)
        self.update_slider_range(self.b_slider, self.bands)
        
        self.single_band = min(self.single_band, self.bands - 1)
        self.r_band = min(self.r_band, self.bands - 1)
        self.g_band = min(self.g_band, self.bands - 1)
        self.b_band = min(self.b_band, self.bands - 1)
        
        self.single_slider.set_val(self.single_band)
        self.r_slider.set_val(self.r_band)
        self.g_slider.set_val(self.g_band)
        self.b_slider.set_val(self.b_band)
        
        self.update_data_list_display()
        self.update_display()
        
    def update_display(self):
        if self.data is None:
            return
            
        if self.display_mode == 'single':
            band_data = self.data[:, :, self.single_band]
            band_data = (band_data - band_data.min()) / (band_data.max() - band_data.min() + 1e-10)
            if self.current_display:
                self.current_display.remove()
            self.current_display = self.ax.imshow(band_data, cmap='gray')
        else:
            r_data = self.data[:, :, self.r_band]
            g_data = self.data[:, :, self.g_band]
            b_data = self.data[:, :, self.b_band]
            
            global_min = min(r_data.min(), g_data.min(), b_data.min())
            global_max = max(r_data.max(), g_data.max(), b_data.max())
            
            r_data = (r_data - global_min) / (global_max - global_min + 1e-10)
            g_data = (g_data - global_min) / (global_max - global_min + 1e-10)
            b_data = (b_data - global_min) / (global_max - global_min + 1e-10)
            
            rgb_data = np.stack([r_data, g_data, b_data], axis=-1)
            if self.current_display:
                self.current_display.remove()
            self.current_display = self.ax.imshow(rgb_data)
            
        self.ax.set_title(f'Mode: {"Single" if self.display_mode == "single" else "RGB"} | Data: {self.data_names[self.current_data_idx]}')
        self.fig.canvas.draw()
        
    def change_display_mode(self, label):
        if self.data is None:
            return
            
        if label == 'Single':
            self.display_mode = 'single'
            self.show_sliders([0])
        else:
            self.display_mode = 'rgb'
            self.show_sliders([1, 2, 3])
            
        self.update_display()
        
    def update_single_band(self, val):
        self.single_band = int(val)
        self.update_display()
        
    def update_rgb_bands(self, val):
        self.r_band = int(self.r_slider.val)
        self.g_band = int(self.g_slider.val)
        self.b_band = int(self.b_slider.val)
        self.update_display()
        
    def on_press(self, event):
        if event.inaxes != self.ax or self.data is None:
            return
            
        self.start_x = event.xdata
        self.start_y = event.ydata
        self.drawing = True
        
        if self.rect is not None:
            self.rect.remove()
            self.rect = None
            
    def on_motion(self, event):
        if not self.drawing or event.inaxes != self.ax:
            return
            
        current_x = event.xdata
        current_y = event.ydata
        
        if self.rect is not None:
            self.rect.remove()
            
        width = current_x - self.start_x
        height = current_y - self.start_y
        self.rect = Rectangle((self.start_x, self.start_y), width, height, 
                             fill=False, edgecolor='red', linewidth=2)
        self.ax.add_patch(self.rect)
        
        x0 = int(min(self.start_x, current_x))
        y0 = int(min(self.start_y, current_y))
        w = int(abs(width))
        h = int(abs(height))
        
        self.crop_info_text.set_text(f'Crop Info:\nStart: ({x0}, {y0})\nWidth: {w}\nHeight: {h}\nSize: {w}x{h}')
        
        self.fig.canvas.draw()
        
    def on_release(self, event):
        if not self.drawing or event.inaxes != self.ax:
            return
            
        self.drawing = False
        
        if self.rect is not None:
            x0 = int(min(self.start_x, event.xdata))
            y0 = int(min(self.start_y, event.ydata))
            x1 = int(max(self.start_x, event.xdata))
            y1 = int(max(self.start_y, event.ydata))
            
            x0 = max(0, x0)
            y0 = max(0, y0)
            x1 = min(self.cols - 1, x1)
            y1 = min(self.rows - 1, y1)
            
            self.crop_x0 = x0
            self.crop_y0 = y0
            self.crop_width = x1 - x0 + 1
            self.crop_height = y1 - y0 + 1
            
            self.crop_info_text.set_text(f'Crop Info:\nStart: ({x0}, {y0})\nWidth: {self.crop_width}\nHeight: {self.crop_height}\nSize: {self.crop_width}x{self.crop_height}')
            
            self.info_text.set_text(f'Data: {self.data_names[self.current_data_idx]}\nRows: {self.rows}\nCols: {self.cols}\nBands: {self.bands}')
            
    def clear_rect(self, event):
        if self.rect is not None:
            self.rect.remove()
            self.rect = None
            self.fig.canvas.draw()
            
        self.crop_x0 = None
        self.crop_y0 = None
        self.crop_width = None
        self.crop_height = None
        
        self.crop_info_text.set_text('Crop Info:\nNo selection')
        
        if self.data is not None:
            self.info_text.set_text(f'Data: {self.data_names[self.current_data_idx]}\nRows: {self.rows}\nCols: {self.cols}\nBands: {self.bands}')
        else:
            self.info_text.set_text('Waiting for data...')
            
    def verify_crop(self, event):
        if self.data is None or self.crop_x0 is None:
            self.info_text.set_text('Please load data and select area')
            return
            
        cropped_data = self.data[self.crop_y0:self.crop_y0+self.crop_height, 
                                  self.crop_x0:self.crop_x0+self.crop_width, :]
        
        verification_text = "=== Crop Verification ===\n"
        verification_text += f"Original Shape: {self.data.shape}\n"
        verification_text += f"Cropped Shape: {cropped_data.shape}\n"
        verification_text += f"Crop Region: ({self.crop_x0}, {self.crop_y0}) to ({self.crop_x0+self.crop_width-1}, {self.crop_y0+self.crop_height-1})\n"
        verification_text += "---\n"
        
        test_bands = min(self.bands, 3)
        for band_idx in range(test_bands):
            original_sample = self.data[self.crop_y0 + 1, self.crop_x0 + 1, band_idx]
            cropped_sample = cropped_data[1, 1, band_idx]
            verification_text += f"Band {band_idx}: Original={original_sample:.6f}, Cropped={cropped_sample:.6f}, Match={np.isclose(original_sample, cropped_sample)}\n"
        
        center_y = self.crop_height // 2
        center_x = self.crop_width // 2
        for band_idx in range(test_bands):
            original_center = self.data[self.crop_y0 + center_y, self.crop_x0 + center_x, band_idx]
            cropped_center = cropped_data[center_y, center_x, band_idx]
            verification_text += f"Band {band_idx} (center): Original={original_center:.6f}, Cropped={cropped_center:.6f}, Match={np.isclose(original_center, cropped_center)}\n"
        
        all_equal = np.array_equal(self.data[self.crop_y0:self.crop_y0+self.crop_height, 
                                             self.crop_x0:self.crop_x0+self.crop_width, :], 
                                   cropped_data)
        verification_text += "---\n"
        verification_text += f"ALL DATA MATCH: {all_equal}"
        
        print("\n" + "="*50)
        print(verification_text)
        print("="*50)
        
        self.info_text.set_text(verification_text)
            
    def save_crop(self, event):
        if self.data is None or self.rect is None:
            self.info_text.set_text('Please load data and select area')
            return
            
        if self.crop_x0 is None or self.crop_y0 is None:
            self.info_text.set_text('Invalid crop area')
            return
            
        cropped_data = self.data[self.crop_y0:self.crop_y0+self.crop_height, 
                                  self.crop_x0:self.crop_x0+self.crop_width, :]
        
        import tkinter as tk
        from tkinter import filedialog
        
        root = tk.Tk()
        root.withdraw()
        file_path = filedialog.asksaveasfilename(defaultextension='.mat', 
                                                filetypes=[('MAT files', '*.mat')])
        
        if file_path:
            sio.savemat(file_path, {'cropped_data': cropped_data})
            self.info_text.set_text(f'Saved!\nFile: {file_path}\nShape: {cropped_data.shape}')
            
    def save_all_crops(self, event):
        if len(self.data_list) == 0 or self.crop_x0 is None:
            self.info_text.set_text('Please load data and select area')
            return
            
        import tkinter as tk
        from tkinter import filedialog
        
        root = tk.Tk()
        root.withdraw()
        dir_path = filedialog.askdirectory()
        
        if not dir_path:
            return
            
        success_count = 0
        for i, data in enumerate(self.data_list):
            if self.crop_height > data.shape[0] or self.crop_width > data.shape[1]:
                continue
                
            cropped_data = data[self.crop_y0:self.crop_y0+self.crop_height, 
                                  self.crop_x0:self.crop_x0+self.crop_width, :]
            
            base_name = self.data_names[i].replace('.mat', '')
            save_path = f'{dir_path}/{base_name}_cropped.mat'
            sio.savemat(save_path, {'cropped_data': cropped_data})
            success_count += 1
            
        self.info_text.set_text(f'Saved {success_count}/{len(self.data_list)} files\nLocation: {dir_path}')
            
    def show(self):
        plt.show()

if __name__ == '__main__':
    viewer = MatDataViewer()
    viewer.show()
