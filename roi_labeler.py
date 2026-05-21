import tkinter as tk
from tkinter import filedialog, messagebox, ttk
import numpy as np
from scipy.io import loadmat, savemat
import matplotlib.pyplot as plt
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
from matplotlib.patches import Rectangle, Polygon
from matplotlib.widgets import LassoSelector
from matplotlib.path import Path

class ROILabeler:
    def __init__(self, root):
        self.root = root
        self.root.title("ROI Labeler")
        self.root.geometry("1200x800")
        
        self.image = None
        self.original_image = None
        self.labels = {}
        self.current_label = ""
        self.rois = []
        self.current_roi = []
        self.polygon_points = []
        self.drawing = False
        self.draw_mode = "rectangle"
        self.canvas = None
        self.ax = None
        self.figure = None
        self.lasso_selector = None
        
        self.setup_ui()
    
    def setup_ui(self):
        self.main_frame = ttk.Frame(self.root)
        self.main_frame.pack(fill=tk.BOTH, expand=True)
        
        self.left_panel = ttk.Frame(self.main_frame, width=200)
        self.left_panel.pack(side=tk.LEFT, fill=tk.Y, padx=5, pady=5)
        
        self.right_panel = ttk.Frame(self.main_frame)
        self.right_panel.pack(side=tk.RIGHT, fill=tk.BOTH, expand=True)
        
        self.setup_left_panel()
        self.setup_right_panel()
    
    def setup_left_panel(self):
        ttk.Label(self.left_panel, text="Control Panel", font=("Arial", 12, "bold")).pack(pady=5)
        
        ttk.Button(self.left_panel, text="Open Mat File", command=self.open_mat_file).pack(fill=tk.X, pady=3)
        
        ttk.Label(self.left_panel, text="Draw Mode:").pack(pady=3)
        self.mode_var = tk.StringVar(value="rectangle")
        ttk.Radiobutton(self.left_panel, text="Rectangle", variable=self.mode_var, value="rectangle", command=self.set_draw_mode).pack(anchor=tk.W)
        ttk.Radiobutton(self.left_panel, text="Polygon", variable=self.mode_var, value="polygon", command=self.set_draw_mode).pack(anchor=tk.W)
        
        ttk.Label(self.left_panel, text="Label Name:").pack(pady=3)
        self.label_entry = ttk.Entry(self.left_panel)
        self.label_entry.pack(fill=tk.X, pady=3)
        self.label_entry.insert(0, "label_1")
        
        ttk.Button(self.left_panel, text="Set Current Label", command=self.set_current_label).pack(fill=tk.X, pady=3)
        
        ttk.Label(self.left_panel, text="Existing Labels:", font=("Arial", 10, "bold")).pack(pady=3)
        self.label_listbox = tk.Listbox(self.left_panel, height=8)
        self.label_listbox.pack(fill=tk.X, pady=3)
        self.label_listbox.bind("<Double-1>", self.select_label)
        
        ttk.Button(self.left_panel, text="Delete Last ROI", command=self.delete_selected_roi).pack(fill=tk.X, pady=3)
        ttk.Button(self.left_panel, text="Clear All ROIs", command=self.clear_all_rois).pack(fill=tk.X, pady=3)
        
        ttk.Button(self.left_panel, text="Save Labels", command=self.save_labels).pack(fill=tk.X, pady=3)
        
        self.status_label = ttk.Label(self.left_panel, text="Status: Waiting for file", foreground="blue")
        self.status_label.pack(pady=5)
        
        ttk.Label(self.left_panel, text="Tips:", font=("Arial", 10, "bold")).pack(pady=3)
        ttk.Label(self.left_panel, text="- Rectangle: drag to draw").pack(anchor=tk.W)
        ttk.Label(self.left_panel, text="- Polygon: click to add points").pack(anchor=tk.W)
        ttk.Label(self.left_panel, text="  Right-click to finish").pack(anchor=tk.W)
    
    def setup_right_panel(self):
        self.figure, self.ax = plt.subplots(1, 1, figsize=(8, 6))
        self.ax.set_title("Image Display")
        self.ax.set_axis_off()
        
        self.canvas = FigureCanvasTkAgg(self.figure, master=self.right_panel)
        self.canvas.get_tk_widget().pack(fill=tk.BOTH, expand=True)
        
        self.canvas.mpl_connect('button_press_event', self.on_mouse_down)
        self.canvas.mpl_connect('button_release_event', self.on_mouse_up)
        self.canvas.mpl_connect('motion_notify_event', self.on_mouse_move)
    
    def set_draw_mode(self):
        self.draw_mode = self.mode_var.get()
        if self.draw_mode == "polygon":
            if self.lasso_selector is not None:
                self.lasso_selector.disconnect_events()
                self.lasso_selector = None
            self.polygon_points = []
            self.status_label.config(text="Polygon mode: Click to add points, right-click to finish")
        else:
            if self.lasso_selector is not None:
                self.lasso_selector.disconnect_events()
                self.lasso_selector = None
            self.polygon_points = []
            self.status_label.config(text=f"Current Label: {self.current_label}")
    
    def set_current_label(self):
        self.current_label = self.label_entry.get().strip()
        if self.current_label and self.current_label not in self.labels:
            self.labels[self.current_label] = len(self.labels)
            self.label_listbox.insert(tk.END, self.current_label)
        if self.draw_mode == "polygon":
            self.status_label.config(text="Polygon mode: Click to add points, right-click to finish")
        else:
            self.status_label.config(text=f"Current Label: {self.current_label}")
    
    def select_label(self, event):
        selected = self.label_listbox.curselection()
        if selected:
            self.current_label = self.label_listbox.get(selected[0])
            self.label_entry.delete(0, tk.END)
            self.label_entry.insert(0, self.current_label)
            if self.draw_mode == "polygon":
                self.status_label.config(text="Polygon mode: Click to add points, right-click to finish")
            else:
                self.status_label.config(text=f"Current Label: {self.current_label}")
    
    def open_mat_file(self):
        file_path = filedialog.askopenfilename(filetypes=[("Mat Files", "*.mat")])
        if not file_path:
            return
        
        try:
            mat_data = loadmat(file_path)
            image_keys = [k for k in mat_data.keys() if not k.startswith('_')]
            
            if len(image_keys) == 0:
                messagebox.showerror("Error", "No image data found in Mat file")
                return
            
            selected_key = image_keys[0]
            if len(image_keys) > 1:
                key_dialog = tk.Toplevel(self.root)
                key_dialog.title("Select Image Data")
                ttk.Label(key_dialog, text="Please select the image data to open:").pack(pady=5)
                listbox = tk.Listbox(key_dialog, width=50)
                for key in image_keys:
                    listbox.insert(tk.END, key)
                listbox.pack(pady=5)
                
                def on_select():
                    nonlocal selected_key
                    selected = listbox.curselection()
                    if selected:
                        selected_key = listbox.get(selected[0])
                    key_dialog.destroy()
                
                ttk.Button(key_dialog, text="OK", command=on_select).pack(pady=5)
                self.root.wait_window(key_dialog)
            
            self.image = mat_data[selected_key]
            self.original_image = self.image.copy()
            
            if self.image.ndim == 3 and self.image.shape[2] == 1:
                self.image = self.image[:, :, 0]
            
            self.display_image()
            self.status_label.config(text=f"Opened: {selected_key}")
            
        except Exception as e:
            messagebox.showerror("Error", f"Failed to open file: {str(e)}")
    
    def display_image(self):
        self.ax.clear()
        
        if self.image.ndim == 3:
            if self.image.shape[2] == 3:
                self.ax.imshow(self.image[..., ::-1])
            else:
                self.ax.imshow(self.image[:, :, 0], cmap='gray')
        else:
            self.ax.imshow(self.image, cmap='gray')
        
        self.ax.set_axis_off()
        self.draw_rois()
        self.draw_polygon_preview()
        self.canvas.draw()
    
    def draw_rois(self):
        for roi in self.rois:
            color = self.get_label_color(roi['label'])
            if roi['type'] == 'rectangle':
                rect = Rectangle((roi['x1'], roi['y1']), roi['x2'] - roi['x1'], roi['y2'] - roi['y1'],
                               fill=False, color=color, linewidth=2)
                self.ax.add_patch(rect)
                self.ax.text(roi['x1'], roi['y1'] - 5, roi['label'], color=color, fontsize=10)
            elif roi['type'] == 'polygon':
                polygon = plt.Polygon(roi['points'], fill=False, color=color, linewidth=2)
                self.ax.add_patch(polygon)
                centroid = np.mean(roi['points'], axis=0)
                self.ax.text(centroid[0], centroid[1], roi['label'], color=color, fontsize=10)
    
    def draw_polygon_preview(self):
        if self.draw_mode == "polygon" and len(self.polygon_points) > 1:
            polygon = plt.Polygon(self.polygon_points, fill=False, color='red', linewidth=2, linestyle='--')
            self.ax.add_patch(polygon)
            
            for i, (x, y) in enumerate(self.polygon_points):
                self.ax.plot(x, y, 'ro', markersize=6)
    
    def get_label_color(self, label):
        colors = ['red', 'blue', 'green', 'yellow', 'magenta', 'cyan', 'orange', 'purple']
        if label in self.labels:
            return colors[self.labels[label] % len(colors)]
        return 'red'
    
    def on_mouse_down(self, event):
        if self.image is None:
            return
        
        if event.button == 1:
            if self.draw_mode == "rectangle" and event.inaxes == self.ax:
                self.drawing = True
                self.current_roi = [event.xdata, event.ydata]
            
            elif self.draw_mode == "polygon" and event.inaxes == self.ax:
                self.polygon_points.append([event.xdata, event.ydata])
                self.display_image()
        
        elif event.button == 3:
            if self.draw_mode == "polygon" and len(self.polygon_points) >= 3:
                points = np.array(self.polygon_points)
                self.add_roi(0, 0, 0, 0, 'polygon', points)
                self.polygon_points = []
                self.display_image()
    
    def on_mouse_up(self, event):
        if not self.drawing or self.image is None:
            return
        
        if self.draw_mode == "rectangle" and event.inaxes == self.ax:
            self.drawing = False
            x1, y1 = self.current_roi
            x2, y2 = event.xdata, event.ydata
            
            if abs(x2 - x1) > 5 and abs(y2 - y1) > 5:
                self.add_roi(min(x1, x2), min(y1, y2), max(x1, x2), max(y1, y2), 'rectangle')
    
    def on_mouse_move(self, event):
        if not self.drawing or self.image is None:
            return
        
        if self.draw_mode == "rectangle" and event.inaxes == self.ax:
            self.display_image()
            x1, y1 = self.current_roi
            x2, y2 = event.xdata, event.ydata
            rect = Rectangle((x1, y1), x2 - x1, y2 - y1, fill=False, color='red', linewidth=2, linestyle='--')
            self.ax.add_patch(rect)
            self.canvas.draw()
    
    def add_roi(self, x1, y1, x2, y2, roi_type, points=None):
        if not self.current_label:
            messagebox.showwarning("Warning", "Please set a label name first")
            if roi_type == 'polygon':
                self.polygon_points = []
            return
        
        roi = {
            'label': self.current_label,
            'type': roi_type,
            'x1': x1,
            'y1': y1,
            'x2': x2,
            'y2': y2,
            'points': points
        }
        
        self.rois.append(roi)
        
        if self.current_label not in self.labels:
            self.labels[self.current_label] = len(self.labels)
            self.label_listbox.insert(tk.END, self.current_label)
        
        self.display_image()
        self.status_label.config(text=f"Added ROI ({len(self.rois)} total)")
    
    def delete_selected_roi(self):
        if len(self.rois) == 0:
            messagebox.showwarning("Warning", "No ROIs to delete")
            return
        
        self.rois.pop()
        self.display_image()
        self.status_label.config(text=f"Deleted ROI ({len(self.rois)} remaining)")
    
    def clear_all_rois(self):
        if messagebox.askyesno("Confirm", "Are you sure to clear all ROIs?"):
            self.rois = []
            self.polygon_points = []
            self.display_image()
            self.status_label.config(text="Cleared all ROIs")
    
    def save_labels(self):
        if len(self.rois) == 0:
            messagebox.showwarning("Warning", "No labels to save")
            return
        
        file_path = filedialog.asksaveasfilename(defaultextension=".mat", filetypes=[("Mat Files", "*.mat")])
        if not file_path:
            return
        
        try:
            label_mask = np.zeros(self.image.shape[:2], dtype=np.int32)
            
            for roi in self.rois:
                label_id = self.labels[roi['label']] + 1
                
                if roi['type'] == 'rectangle':
                    y1, y2 = int(roi['y1']), int(roi['y2'])
                    x1, x2 = int(roi['x1']), int(roi['x2'])
                    y1, y2 = max(0, y1), min(label_mask.shape[0], y2)
                    x1, x2 = max(0, x1), min(label_mask.shape[1], x2)
                    label_mask[y1:y2, x1:x2] = label_id
                elif roi['type'] == 'polygon':
                    points = np.round(roi['points']).astype(np.int32)
                    self.fill_polygon(label_mask, points, label_id)
            
            label_info = {
                'labels': self.labels,
                'rois': self.rois,
                'label_mask': label_mask
            }
            
            savemat(file_path, label_info)
            messagebox.showinfo("Success", f"Labels saved to: {file_path}")
            self.status_label.config(text=f"Saved: {file_path}")
        
        except Exception as e:
            messagebox.showerror("Error", f"Failed to save: {str(e)}")
    
    def fill_polygon(self, mask, points, value):
        if len(points) < 3:
            return
        
        min_x = max(0, np.min(points[:, 0]))
        max_x = min(mask.shape[1] - 1, np.max(points[:, 0]))
        min_y = max(0, np.min(points[:, 1]))
        max_y = min(mask.shape[0] - 1, np.max(points[:, 1]))
        
        path = Path(points)
        
        for y in range(int(min_y), int(max_y) + 1):
            for x in range(int(min_x), int(max_x) + 1):
                if path.contains_point((x, y)):
                    mask[y, x] = value

if __name__ == "__main__":
    root = tk.Tk()
    app = ROILabeler(root)
    root.mainloop()