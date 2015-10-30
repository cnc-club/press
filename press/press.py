#!/usr/bin/env python
# -*- coding: utf-8 -*-
import serial
from time import sleep,time
import pygtk
import gtk
import gobject
import minimalmodbus
from math import *
import numpy as np

from matplotlib.figure import Figure
from matplotlib.backends.backend_gtk import FigureCanvasGTK as FigureCanvas

import sys
import threading
import cairo
from pycha.line import LineChart
from pycha.bar import VerticalBarChart

import ConfigParser


rele = {}
rele["kl0"] = 16
rele["kl1"] = 17
rele["kl2"] = 18
rele["kl3"] = 19
rele["kl4"] = 20
rele["kl5"] = 21
rele["kl6"] = 22
rele["kl7"] = 23

rele["n0"] = 0
rele["n1"] = 1
rele["n2"] = 2
rele["n3"] = 3
rele["n4"] = 4
rele["n5"] = 5
rele["n6"] = 6
rele["n7"] = 7

rele["p0"] = 24
rele["p1"] = 25

tpar = {}
tpar["00"] = 0
tpar["01"] = 1
tpar["02"] = 2
tpar["03"] = 3
tpar["10"] = 4
tpar["11"] = 5
tpar["12"] = 6
tpar["13"] = 7

tpar["04"] = 8
tpar["05"] = 9
tpar["06"] = 10
tpar["07"] = 11
tpar["14"] = 12
tpar["15"] = 13
tpar["16"] = 14
tpar["17"] = 15







class ReadSensors(threading.Thread):
	def __init__(self, mv,temp_labels,temp_stat):
		super(ReadSensors, self).__init__()
		self.mv110 = mv
		self.quit = False
		self.temp_labels = temp_labels
		self.temp_stat = temp_stat
		self.res = [0 for i in range(16)]
		self.i = -1

	def read_temp(self, n):
		mv = self.mv110[n/8]
		v = mv.read_register(n%8*6+1)
		m = mv.read_register(n%8*6+0)
		return float(v)/(10**m)


	def update(self, counter):
		self.i = (self.i + 1)%16
		i = self.i
		t = self.read_temp(tpar["%s%s"%(i/8,i%8)])			
		self.res[i] = t
		if i == 15 :
			for t in range(8) : 
				l = self.temp_labels[t]
				l.set_text("%s,%s"%(self.res[t], self.res[t+8]))		
				self.temp_stat.append(self.res)
		return False

	def run(self):
		counter = 0
		while not self.quit:
			counter += 1
			gobject.idle_add(self.update, counter)
			sleep(0.1)




class Press():

	def lin(x,y,x1,y1,t):
		if abs(x-x1)== 0 : return y+y1/2
		t = (t-y)/(y1-y)
		return (x*(1-t)+x1*t)

	def get_temp(self,n,t):
		i = 1
		t = 0
		while True: 
			y = self.get_conf("Zone%s"%n, "t%s"%i, set_value=False)
			t += self.get_conf("Zone%s"%n, "Время_%s"%i, set_value=False)
			if y==None : break
			p.append((t,y))
		if p[-1][0]<t : return p[-1][1] 	
		if p[0][0]>t : return p[0][1] 	
		for i in range(len(p)) :
			if p[i][0]>t:
				break
		return lin(p[i-1][0],p[i-1][1],p[i][0],p[i][1],t)
			
	def __init__(self):
		self.temp_stat = []
		
		self.config = ConfigParser.RawConfigParser()
		self.config.read('press.ini')
		self.cycle = None
		
		self.mu110 = minimalmodbus.Instrument('/dev/ttyS0', 1) # port name, slave address (in decimal)
		self.mu110.serial.baudrate = 9600   # Baud
		self.mu110.serial.bytesize = 8
		self.mu110.serial.parity   = serial.PARITY_NONE
		self.mu110.serial.stopbits = 1
		self.mu110.serial.timeout  = .05   # seconds
		self.mu110.mode = minimalmodbus.MODE_ASCII 

		self.mv110 = [None,None,None]

		self.mv110[0] = minimalmodbus.Instrument('/dev/ttyS0', 100) # port name, slave address (in decimal)
		self.mv110[0].serial.baudrate = 9600   # Baud
		self.mv110[0].serial.bytesize = 8
		self.mv110[0].serial.parity   = serial.PARITY_NONE
		self.mv110[0].serial.stopbits = 1
		self.mv110[0].serial.timeout  = .05   # seconds
		self.mv110[0].mode = minimalmodbus.MODE_ASCII 

		self.mv110[1] = minimalmodbus.Instrument('/dev/ttyS0', 200) # port name, slave address (in decimal)
		self.mv110[1].serial.baudrate = 9600   # Baud
		self.mv110[1].serial.bytesize = 8
		self.mv110[1].serial.parity   = serial.PARITY_NONE
		self.mv110[1].serial.stopbits = 1
		self.mv110[1].serial.timeout  = .05   # seconds
		self.mv110[1].mode = minimalmodbus.MODE_ASCII 



		#Set the Glade file
		#builder = gtk.Builder()
		#builder.add_from_file("press.glade")
		#self.main = builder.get_object("MainWindow")
		
		self.main = gtk.Window(gtk.WINDOW_TOPLEVEL)
		self.main.connect("delete_event", self.quit)
		self.main.connect("destroy", self.quit)


		self.notebook = gtk.Notebook()
		hbox = gtk.HBox()
		self.notebook.append_page(hbox,gtk.Label("Состояние"))
		f = gtk.Frame()
		f.set_label("Температура")
		t = gtk.Table(2,4)
		f.add(t)
	
		self.temp_labels = [None]*8
		for i in range(8) :
			l = gtk.Label("0,0")
			t.attach(l,i/4,i/4+1,i%4,i%4+1)
			self.temp_labels[i] = l
		
		hbox.pack_start(f)		
#		f = Figure(figsize=(5,4), dpi=100)
#		self.plot = f.add_subplot(111)
#		self.canvas = FigureCanvas(f)  # a gtk.DrawingArea

#		self.plot = LinePlot ()

#		hbox.pack_start(self.plot)		

		vbox = gtk.VBox()
		hbox.pack_start(vbox)		
		b = gtk.ToggleButton("Пуск")
		b.connect("clicked", self.start)
		vbox.pack_start(b)				
		self.cycle_enable = b
		l = gtk.Label("Время в цикле")
		vbox.pack_start(l)
		self.cycle_label = l
		l = gtk.Label("Колчество циклов")
		vbox.pack_start(l)
		self.cycle_num = l

		names = self.config.get("Params", "names").split(" ")
			
		for n in range(8) :
			t = gtk.Table()
			self.notebook.append_page(t,gtk.Label("Зона %s"%n))
			i = 0
			for l in names :
				t.attach(gtk.Label(l),0,1,i,i+1)
				e = gtk.Entry()
				t.attach(e,1,2,i,i+1)
				v = self.get_conf('Zone%s'%n,l)
				e.set_text(str(v))				
				e.connect("changed", self.entry_change,'Zone%s'%n,l)
				i += 1
									

		####	Test panel		####

		tab = gtk.Table(4,8)
		k = 0
		for i in range(8):
			b = gtk.ToggleButton("Клапан %s"%i)
			b.connect("clicked", self.toggle, rele["kl%s"%i])
			tab.attach(b, k/8, k/8+1, k%8, k%8+1)
			k += 1
			
		for i in range(8):
			b = gtk.ToggleButton("Нагреватель %s"%i)
			b.connect("clicked", self.toggle, rele["n%s"%i])
			tab.attach(b, k/8, k/8+1, k%8, k%8+1)
			k += 1
		
		b = gtk.ToggleButton("Пресс вкл!")
		b.connect("clicked", self.press)
		self.press_on = b
		tab.attach(b, k/8, k/8+1, k%8, k%8+1)
		k += 1

		b = gtk.ToggleButton("Пресс нажим!")
		b.connect("clicked", self.press)
		tab.attach(b, k/8, k/8+1, k%8, k%8+1)
		k += 1

		self.notebook.append_page(tab,gtk.Label("Тестовая панель"))
		self.main.add(self.notebook)
		self.main.show_all()				


#		self.serial_thread = threading.Thread(target=self.read_sensors )
#		self.serial_thread_finish = False
#		self.serial_thread.start()

		gobject.threads_init()

 		self.read_sensors_thread = ReadSensors(self.mv110, self.temp_labels, self.temp_stat)
		self.read_sensors_thread.start()
	
		self.timer()
	
	def get_conf(self,s,n, set_value=True):
		print s,n, self.config.has_option(s,n)
		if self.config.has_option(s,n):
			return self.config.get(s,n)
		elif set_value:
			if s not in self.config.sections():
				self.config.add_section(s)
			if not self.config.has_option(s,n):
				self.config.set(s,n,"0")
			return self.config.get(s,n)
		else:
			return None	

	def set_conf(self,s,n,v):
		if s not in self.config.sections():
			self.config.add_section(s)
		if not self.config.has_option(s,n):
			self.config.set(s,n,"0")
		return self.config.set(s,n,v)

	def entry_change(self, e, s,n):
		self.set_conf(s,n,e.get_text())
		
	def read_temp(self, n):
		mv = self.mv110[n/8]
		v = mv.read_register(n%8*6+1)
		m = mv.read_register(n%8*6+0)
		return float(v)/(10**m)
	
	def quit(self,a=None, b=None):
#		self.serial_thread_finish = True
#		self.serial_thread.join()
		self.read_sensors_thread.quit = True
		self.off()
		self.config.write(open("press.ini","w"))
		gtk.main_quit()

		return gtk.FALSE	
		
	
	def timer(self):
		return
	
		l = len(self.temp_stat)	
		d = []
		for i in range(16) :
			s = [ (j,self.temp_stat[j][i]) for j in range(l) ]
			d.append(("%s"%i,s)) 
		self.plot.set_data_(d)
		
		self.plot._options = {
	      	'legend': {
            'hide': True}	 ,
            "shouldFill": False,            
            'background': 
            	{
	            'color': '#eeeeff',
	            'lineColor': '#444444'
		        },
            }

#		self.canvas.draw()

		return True	
	
				
	def press(self,b) :
		if self.press_on.get_active() and b!=self.press_on:
			if b.get_active():
				self.mu110.write_register(rele["p0"], 0, 0) # Registernumber, value, number of decimals for storage
				self.mu110.write_register(rele["p1"], 1000, 0) # Registernumber, value, number of decimals for storage
			else :
				self.mu110.write_register(rele["p1"], 0, 0) # Registernumber, value, number of decimals for storage
				self.mu110.write_register(rele["p0"], 1000, 0) # Registernumber, value, number of decimals for storage
		else :
				self.mu110.write_register(rele["p1"], 0, 0) # Registernumber, value, number of decimals for storage
				self.mu110.write_register(rele["p0"], 0, 0) # Registernumber, value, number of decimals for storage

	def off(self,a=0,b=0) :
		self.mu110.write_register(96, 0, 0) # Registernumber, value, number of decimals for storage
		self.mu110.write_register(97, 0, 0) # Registernumber, value, number of decimals for storage
			
	def turn_on(self, n, v = 1000):
		self.mu110.write_register(n, v, 0) # Registernumber, value, number of decimals for storage
	def turn_off(self, n, v = 1000):
		self.mu110.write_register(n, 0, 0) # Registernumber, value, number of decimals for storage

	
    
	def toggle(self, b, k):
		if b.get_active():
			self.turn_on(k)
		else :
			self.turn_off(k)
	

	def start(self, b):
		if b.get_active() :
			gtk.timeout_add(5000, self.operate) # call every min		
			self.cycle = time()
			
			
	def turn_on_timer(self,n,t):
		self.turn_on(n)
		gtk.timeout_add(t*1000, self.turn_off,n) # call every min		


	def operate(self) :
		if not self.cycle_enable.get_active() :
			return False	

		t = time() - self.cycle
		self.cycle_label.set_text("Время цикла: %02.0f:%02.0f"%((t/60),(t%60) )) 

		t1 = [160,150,130,100,160,150,130,100]
		
		t = self.temp_stat[-1]
		print t
		for i in range(8):
			if t[i]<t1[1]-5: 
				self.turn_on(rele["n%s"%i])
			else : 
				self.turn_off(rele["n%s"%i])
			if t[i]>t1[1]: 
				self.turn_on(rele["kl%s"%i])
			else :
				self.turn_off(rele["kl%s"%i])
#		for i in range(8) :
#			t = self.get_temp(i,time()-self.cycle)
#			print i,t

		return True



        


if __name__ == "__main__":
	press = Press()
	gtk.main()

