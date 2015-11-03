#!/usr/bin/env python
# -*- coding: utf-8 -*-
from time import *
from pid import PID
import ConfigParser
import pygtk
import gtk
import gobject

press_update_int = 5000

class Zone() :

	def __init__(self, i, press) :
		self.i = i
		self.pid = PID()
		self.t = 0
		self.prog = [[10,12,34,5,700,5],[100,200,200,123,10,0]]
		self.press = press
		self.t = []
		self.get_conf()
		
	def get_conf(self) :
		self.heater_n = self.press.get_conf("Zone%s"%self.i, "heater") 
		self.cooler_n = self.press.get_conf("Zone%s"%self.i, "cooler") 
		self.t_n = self.press.get_conf("Zone%s"%self.i, "t_n") 
		self.t1_n = self.press.get_conf("Zone%s"%self.i, "t1_n") 
		self.dead_band = self.press.get_conf("Zone%s"%self.i, "Мертвая_зона") 
		#self.pid.Kp = self.press.get_conf("Zone%s"%self.i, "p") 
		#self.pid.Ki = self.press.get_conf("Zone%s"%self.i, "i") 
		#self.pid.Kd = self.press.get_conf("Zone%s"%self.i, "d") 

		i = 0
		t = 0
		while True: 
			y = self.press.get_conf("Zone%s"%self.i, "t%s"%i, set_value=False)
			if y==None : break
			t += self.press.get_conf("Zone%s"%self.i, "Время_%s"%i, set_value=False)
			self.prog.append((t,y))
			i += 1

	def update(self, cycle) :
		#self.pid.set_point = self.get_command(cycle)
		#c = self.pid.update(self.t)
		c = self.get_temp() - self.get_command(cycle)
		if c > self.dead_band :
			c = min(c,self.max_heat_t)
			self.heater_off = time()+min(self.max_t, c*self.temp_k)
			self.heater = True
			self.cooler = False
		elif c < -self.dead_band :
			c = min(-c,self.max_heat_t)
			self.cooler_off = time()+min(self.max_t, c*self.temp_k)
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
#		print cycle, i, t, t1, t_,
		return float(self.prog[1][i+1] - self.prog[1][i]) * t_ + self.prog[1][i]


class Push() :
	def __init__(self, press) :	
		self.press = press

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
		self.pid.Kp = self.press.get_conf("Push", "p") 
		self.pid.Ki = self.press.get_conf("Push", "i") 
		self.pid.Kd = self.press.get_conf("Push", "d") 
		self.dead_band = self.press.get_conf("Push", "Мертвая_зона")
		self.max_t = self.press.get_conf("Push", "max_t") 		

		self.prog = []		
		while True: 
			y = self.press.get_conf("Push", "t%s"%i, set_value=False)
			t += self.press.get_conf("Push", "Время_%s"%i, set_value=False)
			if y==None : break
			self.prog.append((t,y))

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
		self.log_file = open("log-%s.csv"%strftime("%Y-%m-%d %H:%M:%S"),"w")
		
	def init_gtk(self) :
		self.main = gtk.Window(gtk.WINDOW_TOPLEVEL)
		self.main.connect("delete_event", self.quit)
		self.main.connect("destroy", self.quit)
	
		self.notebook = gtk.Notebook()

		t = gtk.Table(2,8)
		f = gtk.Frame()
		f.add(t)
		f.set_label("Температура")

		hbox = gtk.HBox()
		hbox.pack_start(f)		

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
		
		l = gtk.Label("Время в цикле")
		vbox.pack_start(l)
		self.cycle_label = l
		
		l = gtk.Label("Колчество циклов")
		vbox.pack_start(l)
		self.cycle_num = l

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
		self.read_sensors_thread.quit = True
		self.off()
		self.config.write(open("press.ini","w"))
		gtk.main_quit()
		return gtk.FALSE	

	def stop(self, *arg) :
		self.running = False
		self.off()		

	def off(self, *arg) :
		self.mu110.write_register(0x62, 0, 0) # Registernumber, value, number of decimals for storage
		self.mu110.write_register(0x61, 0, 0) # Registernumber, value, number of decimals for storage

	def start(self, *arg) :
		self.running = True
		self.cycle = 0
		self.start_time = time()
		gobject.timeout_add(press_update_int, self.run) # call every min		
	
	
	def log(self) :	
		self.log_file.write(strftime("%Y-%m-%d %H:%M:%S"), self.state)
		

	def run(self) :
		if not self.running :
			return False		
		else :	
			self.cycle = time() - self.start_time		
			
			return True	
			


	def get_conf(self,s,n, set_value=True):
		print s,n, self.conf.has_option(s,n)
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

	

	def update_rs(self, c=0, off=False) :
		n = 32
		
		if n % 2 or off :
			# write rele
			state = [False for i in range(32)]
			
			for z in self.z :
 				state[z.heater_n] = z.heater
			
			state[self.push.down_n] = self.push.down
			state[self.push.up_n] = self.push.up
 				
 			t, t1 = 0,0
			for i in range(16):
				t |= (1<<i)*state[i]
				t1 |= (1<<i)*state[i+16]
			
			if self.state != state :
				self.mu110.write_register(0x62, t, 0) # Registernumber, value, number of decimals for storage
				self.mu110.write_register(0x61, t1, 0) # Registernumber, value, number of decimals for storage
	
		if c%n<17 :
			# read temp
			mv = self.mv110[c%17/8]
			v = mv.read_register(c%8*6+1)
			m = mv.read_register(c%8*6+0)
			self.sens[c] = float(v)/(10**m)		
		
		
		
						
	def update(self) :
		counter = 0
		while not self.quit:
			counter += 1
			gobject.idle_add(self.update_rs, counter)
			sleep(0.1)
	
	def operate(self):
		pass


if __name__ == "__main__":
	press = Press()
	gtk.main()

