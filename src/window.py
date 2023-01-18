#!/scratch/users/nifuchs/bin/anaconda2/ipython
# -*- coding: utf-8 -*-

import tkinter as tk
from tkinter import font
import numpy as np
import matplotlib
matplotlib.use("TkAgg")
try:
    from matplotlib.backends.backend_tkagg import NavigationToolbar2TkAgg
except ImportError:
    from matplotlib.backends.backend_tkagg import NavigationToolbar2Tk as NavigationToolbar2TkAgg
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
import matplotlib.pyplot as plt
import os
import argparse

import matplotlib.cm as cm
from roipoly import *
from copy import copy

class TrainingWindow:

    def __init__(self, thumb, classdict, filename,segment_dict):
        """Constructor"""
        #Variables
        self.parent = tk.Tk()
        #self.rgb = rgb
        self.thumb = thumb
        self.segment_dict = segment_dict
        self.surf_class = 8
        self.color='r'
        self.filename = filename
        self.old_flag = 1
        self.lock_flag = False
        if len(segment_dict) == 0:
            self.old_flag = 0
            for i in range(len(classdict.keys())):
                self.segment_dict[i] = []
        self.classdict=classdict
        
        self.parent.title("Training Creation")
        frame = tk.Frame(self.parent)
        frame.pack(side='left')
        buttons = tk.Frame(self.parent)
        buttons.pack(side='right')
    
        
        if len(self.classdict.keys()) == 11:
            waterBtn = tk.Button(self.parent, text=self.classdict['water'][2], width=16, height=2, highlightbackground=self.classdict['water'][1],
                command=lambda: self.classify('water'))
            waterBtn.pack(in_=buttons, side='top')
            snowBtn = tk.Button(self.parent, text=self.classdict['snow'][2], width=16, height=2, highlightbackground=self.classdict['snow'][1],
                command=lambda: self.classify('snow'))
            snowBtn.pack(in_=buttons, side='top')

        
        
        spacer1 = tk.Button(self.parent, text="  ", width=16, height=2)
        spacer1.pack(in_=buttons,side="top")
        spacer3 = tk.Button(self.parent, text="Delete last", width=16, height=2, command=lambda: self.delete_last_segment())
        spacer3.pack(in_=buttons,side="top")
        spacer1 = tk.Button(self.parent, text="Delete all", width=16, height=2, command=lambda: self.delete_all())
        spacer1.pack(in_=buttons,side="top")
        quitBtn = tk.Button(self.parent, text="Next image", width=16, height=2, command=lambda: self.quit())
        quitBtn.pack(in_=buttons, side='top')
        
        
        #Creating the canvas where the images will be
        self.fig = plt.figure(figsize=[10,7])
        self.fig.subplots_adjust(left=0.01,right=0.99,bottom=0.05,top=0.99,wspace=0.01,\
        hspace=0.01)
        canvas = FigureCanvasTkAgg(self.fig, frame)
        toolbar = NavigationToolbar2TkAgg(canvas, frame)
        canvas.get_tk_widget().pack(in_=frame, side='top')
        toolbar.pack(in_=frame, side='top')
        #toolbar = NavigationToolbar2TkAgg(canvas, self.parent)
        #toolbar.update()
        #canvas._tkcanvas.pack(side=tk.TOP, fill=tk.BOTH, expand=1)
        
        
        self.display_rgb()
        
        if self.old_flag:
            self.plot_old_segments()
        
        self.parent.mainloop()
        
    def delete_all(self):
        for i in range(8):
            self.segment_dict[i] = []
        self.display_rgb()
        self.old_flag=0
        
    def delete_last_segment(self):
        self.segment_dict[self.surf_class] = self.segment_dict[self.surf_class][:-1]
        d_len = len(self.ax.lines) - self.line_len
        for n in range(d_len):
            self.ax.lines.remove(self.ax.lines[-1])
        self.fig.canvas.draw()
    
    def plot_old_segments(self):
        
        for surf_class in self.classdict.keys():
            n_class = self.classdict[surf_class][0]
            for poly in range(len(self.segment_dict[n_class])):
                my_cmap = copy(cm.jet)
                my_cmap.set_under('k',alpha=0)
                my_cmap.set_over(self.classdict[surf_class][1])
                self.ax.imshow(np.float32(self.segment_dict[n_class][poly]),clim=[0.2, 0.8],cmap=my_cmap)
                self.fig.canvas.draw()
                
    def display_rgb(self):
    
        plt.cla()

        #Plotting onto the GUI
        self.ax = self.fig.add_subplot(1,1,1)
        self.ax.imshow(np.uint8(self.thumb),interpolation='None',vmin=0,vmax=255)
        self.ax.tick_params(
        axis='both',          # changes apply to the x-axis
        which='both',      # both major and minor ticks are affected
        bottom='off',      # ticks along the bottom edge are off
        top='off',         # ticks along the top edge are off
        left='off',
        right='off',
        labelleft='off',
        labelbottom='off')

        #Updating the plots
        self.fig.canvas.draw()
        #plt.show(block=True)
        
    def choose_roi(self):
        #plt.ion()
        ROI = roipoly(fig=self.fig,ax=self.ax,roicolor=self.color,parent=self.parent)
        self.segment_dict[self.surf_class].append(ROI.getMask(self.thumb[:,:,0]))
        #self.lock_flag=False
        
    def classify(self, keypress):
        # 0:open water, 1:melt pond, 2: dark/thin ice, 3: snow/ice, 4: shadow pond, 5: shadow snow/ice, 6: ridge area, 7: submerged ice
        #if self.lock_flag:
        #    return None
        #self.lock_flag = True
        self.surf_class = self.classdict[keypress][0]
        self.color = self.classdict[keypress][1]
        self.line_len = len(self.ax.lines)
        self.choose_roi()

    def quit(self):
        #np.save(self.filename, np.array(self.segment_dict))
        plt.close('all')
        self.parent.destroy()
        self.parent.quit()
