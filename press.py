#!/usr/bin/env python
# -*- coding: utf-8 -*-
from time import *
from pid import PID
import ConfigParser
import pygtk
import gtk
import gobject
import minimalmodbus
import serial

press_update_int = 1000

class Zone() :

	def __init__(self, i, press) :
		self.i = i
		self.pid = PID()
		self.t = 0
		self.prog = [[],[]]
		self.press = press
		self.t = []
		self.get_conf()
		self.done = False
		self.temp_k = 1.
		self.heater = False
		self.cooler = False
		self.c = 0
		self.get_conf()
		
	def get_conf(self) :
		self.heater_n = int(self.press.get_conf("Zone%s"%self.i, "heater") )
		self.cooler_n = int(self.press.get_conf("Zone%s"%self.i, "cooler") )
		self.t_n = int(self.press.get_conf("Zone%s"%self.i, "t_n") )
		self.t1_n = int(self.press.get_conf("Zone%s"%self.i, "t1_n") )
		self.dead_band = float(self.press.get_conf("Zone%s"%self.i, "Мертвая_зона") )
		self.max_heat_t = float(self.press.get_conf("Zone%s"%self.i, "max_heat_t") )
		
		#self.pid.Kp = self.press.get_conf("Zone%s"%self.i, "p") 
		#self.pid.Ki = self.press.get_conf("Zone%s"%self.i, "i") 
		#self.pid.Kd = self.press.get_conf("Zone%s"%self.i, "d") 
		prog = self.press.get_conf("Zone%s"%self.i, "prog") 
		i = 1
		t = 0
		for t in prog :
			self.prog[0].append(t[0])
			self.prog[1].append(t[1])
		print self.prog	

	def get_temp(self, t=0) :
		return self.press.sens[self.t_n if t==0 else self.t1_n]

	def __repr__(self) :
		return "Zone %s: t=%.1f t1=%.1f c=%.1f h=%s c=%s"%(self.i, self.get_temp(), self.get_temp(1),self.c, self.heater, self.cooler)

	def update(self, cycle) :
		#self.pid.set_point = self.get_command(cycle)
		#c = self.pid.update(self.t)
		print self.prog
		self.done = sum(self.prog[0])<cycle
		c = self.get_command(cycle) - self.get_temp()
		self.c = c
		if c > self.dead_band :
			c = min(c,self.max_heat_t)
			self.heater_off = time()+min(self.max_heat_t, c*self.temp_k)
			self.heater = True
			self.cooler = False
		elif c < -self.dead_band :
			c = min(-c,self.max_heat_t)
			self.cooler_off = time()+min(self.max_heat_t, c*self.temp_k)
			self.heater = False
			self.cooler = True
	
	def off_update(self):
		if self.heater and self.heater_off < time() :
			self.heater = False
			self.press.update_rs(off=True)

		if self.cooler and self.cooler_off < time() :
			self.cooler = False
			self.press.update_rs(off=True)
		
	def get_command(self, cycle) :
		t = 0 
		if cycle <= 0:
			return self.prog[1][0]
		if cycle >= sum(self.prog[0])-self.prog[0][-1] :
			return self.prog[1][-1]
		
		for i in range(len(self.prog[0])) :
			t += self.prog[0][i]
			if t>cycle :
				break
		t1 = t - self.prog[0][i]		
		
		t_ = float(cycle - t1)/(t-t1)
		c = float(self.prog[1][i+1] - self.prog[1][i]) * t_ + self.prog[1][i]
		print c, self.prog[1]
		return c


class Push() :
	def __init__(self, press) :	
		self.press = press
		self.get_conf(press.conf)
		
	def get_fb(self) :
		return self.press.sens[self.sens_n]
		
	def update(self, cycle) :
		#self.pid.set_point = self.get_command(cycle)
		#c = self.pid.update(self.t)
		c = self.get_command(cycle)
		fb = self.get_fb()
		c = c-fb
		if c > self.dead_band :
			c = min(c,self.max_t)
			self.push_off = time()+c
			self.push = True
			self.pull = False
		else :					
			self.push = False
			self.pull = False

	def release(self) :
		if self.get_fb() > 100 :
			self.push = False
			self.pull = True
			self.pull_off = time()+5
	
	def off_update(self) :
		if self.push and time()>self.push_off :
			self.push = False
			self.press.update_rs(off=True)
		if self.pull and time()>self.pull_off :
			self.pull = False
			self.press.update_rs(off=True)
	
		

	def get_conf(self, conf) :
		self.down_n = self.press.get_conf("Push", "down_n") 
		self.up_n = self.press.get_conf("Push", "up_n") 
		self.up_n = self.press.get_conf("Push", "sens_n") 
#		self.pid.Kp = self.press.get_conf("Push", "p") 
#		self.pid.Ki = self.press.get_conf("Push", "i") 
#s		self.pid.Kd = self.press.get_conf("Push", "d") 
		self.dead_band = self.press.get_conf("Push", "Мертвая_зона")
		self.max_t = self.press.get_conf("Push", "max_t") 		
		self.sens_n = int(self.press.get_conf("Push", "sens_n"))

		self.prog = []		
		i = 1
		t = 0
		while True: 
			y = self.press.get_conf("Push", "t%s"%i, set_value=False)
			if y==None : break
			t += self.press.get_conf("Push", "Время_%s"%i, set_value=False)
			self.prog.append((t,y))
			i+=1
class Press():
	def __init__(self) :

		self.conf = ConfigParser.RawConfigParser()
		self.conf.read('press.ini')		
		self.zones = []
		for i in range(8) :
			z = Zone(i, self)
			z.get_conf()
			self.zones.append(z)
		self.sens = [0. for i in range(24)]
		self.rele = []
		self.inv = []
		self.running = False
		self.init_gtk()
		self.log_file = open("log/log-%s.csv"%strftime("%Y-%m-%d %H:%M:%S"),"w")
		self.cycle_count = 0
		self.init_rs()
		self.off()
		self.rs_read_counter = 0
		self.push = Push(self)
		self.state = [0 for i in range(32)]
	
	def init_rs(self) :
	
	
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

		self.mv110[2] = minimalmodbus.Instrument('/dev/ttyS0', 230) # port name, slave address (in decimal)
		self.mv110[2].serial.baudrate = 9600   # Baud
		self.mv110[2].serial.bytesize = 8
		self.mv110[2].serial.parity   = serial.PARITY_NONE
		self.mv110[2].serial.stopbits = 1
		self.mv110[2].serial.timeout  = .05   # seconds
		self.mv110[2].mode = minimalmodbus.MODE_ASCII 


		
	def init_gtk(self) :
		self.main = gtk.Window(gtk.WINDOW_TOPLEVEL)
		self.main.connect("delete_event", self.quit)
		self.main.connect("destroy", self.quit)
	
		self.notebook = gtk.Notebook()
		
		t = gtk.Table(2,8)
		f = gtk.Frame()
		f.add(t)
		f.set_label("Температура")
		
		vbox = gtk.VBox()		
		vbox.pack_start(f)		

		l = gtk.Label("0") 
		self.push_label = l
		f = gtk.Frame()
		f.add(l)
		f.set_label("Давление")
		vbox.pack_start(f)				
		
		hbox = gtk.HBox()
		hbox.pack_start(vbox)		

		self.notebook.append_page(hbox,gtk.Label("Состояние"))
	
		self.temp_labels = []
		for i in range(8) :
			l = gtk.Label("0")
			t.attach(l,0,1,i,i+1)
			self.temp_labels.append(l)
			
			l = gtk.Label("0")
			t.attach(l,1,2,i,i+1)
			self.temp_labels.append(l)

		vbox = gtk.VBox()		

		b = gtk.ToggleButton("Пуск")
		b.connect("clicked", self.start)
		vbox.pack_start(b)				
		self.cycle_enable = b

		b = gtk.ToggleButton("Стоп")
		b.connect("clicked", self.stop)
		vbox.pack_start(b)				
		self.stop = b
		
		t = gtk.Table()
		l = gtk.Label("Время в цикле")
		l = t.attach(l,0,1,0,1)
		
		l = gtk.Label("00:00:00")
		t.attach(l,1,2,0,1)
		self.cycle_label = l
		
		l = gtk.Label("Колчество циклов")
		t.attach(l,0,1,1,2)

		l = gtk.Label("0")
		t.attach(l,1,2,1,2)
		self.cycle_num = l

		vbox.pack_start(t)
		hbox.pack_start(vbox)		

		i = 0
		for n in self.zones :
			t = gtk.Table()
			i = 0
			#self.notebook.append_page(t,gtk.Label("Зона %s"%n))
									

		####	Test panel		####

		self.main.add(self.notebook)
		self.main.show_all()				


	def quit(self, *arg) :
		self.off()
#		self.conf.write(open("press.ini","w"))
		gtk.main_quit()
		return gtk.FALSE	

	def stop(self, *arg) :
		self.running = False
		self.off()		

	def off(self, *arg) :
		for z in self.zones :
			z.heater = False
			z.cooler = False			
		self.mu110.write_register(0x62, 0, 0) # Registernumber, value, number of decimals for storage
		self.mu110.write_register(0x61, 0, 0) # Registernumber, value, number of decimals for storage

	def start(self, *arg) :
		self.running = True
		self.cycle = 0
		self.start_time = time()
		gobject.timeout_add(press_update_int, self.run) # call every min		
		gobject.idle_add(self.update_rs)
	
	def log(self) :	
		self.log_file.write(strftime("%Y-%m-%d %H:%M:%S"), self.state)
		



	def run(self) :
		if not self.running :
			return False
		else :	
			self.cycle = time() - self.start_time
			c = int(self.cycle)
			self.cycle_label.set_text("%02d:%02d:%02d"%(c/3600,c/60%60,c%60) )
			done = True
			for z in self.zones :
				z.update(self.cycle)
				done = done and z.done
#				print z
			if done :
				self.cycle_count += 1	
				self.cycle_num.set_text("%s"%self.cycle_count)
				self.cycle = 0
				self.start_time = time()
			return True	
			


	def get_conf(self,s,n, set_value=True):

		if self.conf.has_option(s,n):
			return self.conf.get(s,n)
		elif set_value:
			if s not in self.conf.sections():
				self.conf.add_section(s)
			if not self.conf.has_option(s,n):
				self.conf.set(s,n,"0")
			return self.conf.get(s,n)
		else:
			return None	

	

	def update_rs(self, off=False) :
		
		if True :
			# write rele
			state = [False for i in range(32)]
			
			for z in self.zones :
 				state[z.heater_n] = z.heater
 				state[z.cooler_n] = z.cooler
			
			#state[self.push.down_n] = self.push.down
			#state[self.push.up_n] = self.push.up
# 			print state 
 #			print self.state
 			if self.state != state :
	 			t, t1 = 0,0
				for i in range(16):
					t |= (1<<i)*state[i]
					t1 |= (1<<i)*state[i+16]
			
				self.mu110.write_register(0x62, t, 0) # Registernumber, value, number of decimals for storage
				self.mu110.write_register(0x61, t1, 0) # Registernumber, value, number of decimals for storage
		
		n = 17
		c = self.rs_read_counter%n

		# read temp
		mv_ = c/8
		mv = self.mv110[mv_]
		n_ = c%8*6
		v = mv.read_register(n_+1)
		m = mv.read_register(n_+0)
		self.sens[c] = float(v)/(10**m)	
		
		if c == 0 :
			i = 0
			for z in self.zones:
				self.temp_labels[i].set_text("%.1f"%self.sens[z.t_n])
				self.temp_labels[i+1].set_text("%.1f"%self.sens[z.t1_n])
				i += 2
			self.push_label.set_text("%.1f тонн"%self.sens[self.push.sens_n])
			
		self.rs_read_counter += 1	
			
		return True
						
	
	
	def operate(self):
		pass


if __name__ == "__main__":
	press = Press()
	gtk.main()

