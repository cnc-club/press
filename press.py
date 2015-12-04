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
import subprocess
press_update_int = 1000
PCH_K = 1600./3.9

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
		self.last_cooler_timer = 0
		
		
	def get_conf(self) :
		self.heater_n = int(self.press.get_conf("Zone%s"%self.i, "heater") )
		self.cooler_n = int(self.press.get_conf("Zone%s"%self.i, "cooler") )
		self.t_n = int(self.press.get_conf("Zone%s"%self.i, "t_n") )
		self.t1_n = int(self.press.get_conf("Zone%s"%self.i, "t1_n") )
		self.dead_band = float(self.press.get_conf("Zone%s"%self.i, "Мертвая_зона") )
		self.max_heat_t = float(self.press.get_conf("Zone%s"%self.i, "max_heat_t") )
		self.cooler_idle_time = float(self.press.get_conf("Params", "cooler_idle_time") )
		
		
		#self.pid.Kp = self.press.get_conf("Zone%s"%self.i, "p") 
		#self.pid.Ki = self.press.get_conf("Zone%s"%self.i, "i") 
		#self.pid.Kd = self.press.get_conf("Zone%s"%self.i, "d") 
		prog = eval(self.press.get_conf("Prog", "Zone%s"%(self.i%4+1)))
		i = 1
		t = 0
		self.prog = [[],[]]
		for t in prog :
			self.prog[1].append(t[0])
			self.prog[0].append(t[1])


	def get_temp(self, t=0) :
		return self.press.sens[self.t_n if t==0 else self.t1_n]

	def __repr__(self) :
		return "Zone %s: t=%.1f t1=%.1f c=%.1f h=%s c=%s"%(self.i, self.get_temp(), self.get_temp(1),self.c, self.heater, self.cooler)

	def update(self, cycle) :
		#self.pid.set_point = self.get_command(cycle)
		#c = self.pid.update(self.t)
		self.done = sum(self.prog[0])<cycle
		c = self.get_command(cycle) - self.get_temp()
		self.c = c, self.get_command(cycle), self.dead_band	
		
		if c > self.dead_band and self.last_cooler_timer<time() :
			c = min(c,self.max_heat_t)
			self.heater_off = time()+min(self.max_heat_t, c*self.temp_k)
			self.heater = True
			self.cooler = False
		elif c < -self.dead_band :
			c = min(-c,self.max_heat_t)
			self.cooler_off = time()+min(self.max_heat_t, c*self.temp_k)
			self.heater = False
			self.cooler = True
			self.last_cooler_timer	= time()+self.cooler_idle_time			
		else :	
			if self.cooler: 
				 self.last_cooler_timer	= time()+self.cooler_idle_time
			self.heater = False
			self.cooler = False
			
	
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
		return c


class Push() :
	def __init__(self, press) :	
		self.press = press
		self.get_conf(press.conf)
		self.pch = press.pch
		self.releasing = False
		self.release_timer = 0.
		
	def __repr__(self) : 
		t=  self.release_timer - time()  
		return ("Push " + ("\\/ " if self.push else "-- ") + 
				 ("/\\/ " if self.pull else "-- ") +
				  "%.1f %.1f "%(self.freq, self.get_fb())  +
				  "(%.1f) "%self.get_command(self.press.cycle) +
				  "(releasing: %s %s)"% (self.releasing,("%.1f "%t if t>0 else "" ))
				  
				  
			)
		
	def get_fb(self) :
		k = 0.2
		return self.press.sens[self.sens_n] * k
		
	
	def set_freq(self, f=0, rappid = False) :
		if rappid :  
			f = 33.
		self.freq = f*PCH_K
		
	
	def update(self, cycle) :
		#self.pid.set_point = self.get_command(cycle)
		#c = self.pid.update(self.t)
		if self.releasing != False : 
			return
		c = self.get_command(cycle)
		fb = self.get_fb()
		c = c-fb

		if c > self.dead_band :
			c = min(c,self.max_t)
			self.push_off = time()+c
			if self.get_fb()<1 :
				self.set_freq(4.)
			else: 
				self.set_freq(.4)
			
			self.push = True
			self.pull = False
		elif c < -self.dead_band :
			self.set_freq(0)
			self.push = False
			self.pull = True
		else :				
			self.set_freq(0)	
			self.push = False
			self.pull = False

	def pch_read() :
		pass
	

	def release(self, release=None) :
		if release == False : 
			if not self.press.release_button.get_active() :
				self.releasing = False
		if release or (self.press.release_button.get_active() and (self.releasing == False) ) :
			self.releasing = "start release"
			
		if self.releasing  == "start release" : 
			self.push = False
			self.pull = True
			self.set_freq(rappid = True)
			if self.get_fb() < 2 :
				self.releasing = "pull up"
		if self.releasing  == "pull up" : 
			self.release_timer = time() + 5
			self.releasing = "wait"
		if self.releasing == "wait" :
			if self.release_timer < time() :
				self.push = False
				self.pull = False
				self.set_freq(0)
				self.releasing = "done"

		
	
	def off_update(self) :
		if self.push and time()>self.push_off :
			self.push = False
			self.press.update_rs(off=True)
		if self.pull and time()>self.pull_off :
			self.pull = False
			self.press.update_rs(off=True)
	


	def get_conf(self, conf) :
		self.push_n = int(self.press.get_conf("Push", "push_n") )
		self.pull_n = int(self.press.get_conf("Push", "pull_n") )
		self.sens_n = int(self.press.get_conf("Push", "sens_n") )
		self.dead_band = float(self.press.get_conf("Push", "Мертвая_зона"))
		self.max_t = float(self.press.get_conf("Push", "max_t") 		)
		
		self.prog = [[],[]]
		self.push = False
		self.pull = False	
		self.freq = 0
		
		prog = eval(self.press.get_conf("Prog", "Push")) 
		i = 1
		t = 0
		self.prog = [[],[]]
		for t in prog :
			self.prog[1].append(t[0])
			self.prog[0].append(t[1])



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
		return c

			
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
		self.log_file = open("log/log-%s.csv"%strftime("%Y-%m-%d %H:%M:%S"),"w+")
		self.log_file.write(strftime("%Y-%m-%d %H:%M:%S,	")+ "Z1T0,	Z1T1,	Z2T0,	Z2T1,	Z3T0,	Z3T1,	Z4T0,	Z4T1,	Z5T0,	Z5T1,	Z6T0,	Z6T1,	Z7T0,	Z7T1,	Z8T0,	Z8T1,	Pressure\n")
		gobject.timeout_add(10000, self.log) # call every min
		self.cycle_count = 0
		self.init_rs()
		self.rs_read_counter = 0
		self.push = Push(self)
		self.state = [0 for i in range(32)]
		self.last_graph_update = 0
		self.graph_list = [[],[],[],[],[]]
		gobject.idle_add(self.update_rs)	
		self.cycle = 0
		self.init_linuxcnc()
		self.cycle_move = float(self.get_conf("Prog", "move"))
		self.press_prog = ["prog", "release", "wait release", "move"]
		self.freq_state = -1
		self.label_update_timer = -1
		self.off()

	def __repr__(self) :
		return ("<Press> "+ "c=%.1f %s %s\n"%(self.cycle,  self.running, self.press_prog)+
				"%s\n"%self.push +
				"0      70        70      7\n" +
				"".join([ "1" if i else "0" for i in self.state]) +
				"\n\n"
				)
	def init_linuxcnc(self) :
		print "Start halrun"	
		subprocess.Popen(["halrun"])
		sleep(0.5)
		print "Exec press.hal"		
		subprocess.call(["halcmd", "-f", "press.hal"])
		
	
	def move(self, x) :
		p = subprocess.Popen("halcmd getp stepgen.0.position-fb", stdout=subprocess.PIPE, shell=True)
		pos  = p.communicate()[0]
		print "pos" , pos	
		pos = float(pos)
		subprocess.call(("halcmd setp stepgen.0.position-cmd %s"%(pos+x) ).split())
		print pos+x
	
	def test(self, *arg) :	
		self.move(20)
		 
	
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


		pch = minimalmodbus.Instrument('/dev/ttyS0', 150) # port name, slave address (in decimal)
		pch.serial.baudrate = 9600   # Baud
		pch.serial.bytesize = 8
		pch.serial.parity   = serial.PARITY_NONE
		pch.serial.stopbits = 1
		pch.serial.timeout  = .15   # seconds
		pch.mode = minimalmodbus.MODE_ASCII 
		pch = minimalmodbus.Instrument('/dev/ttyS0', 150) # port name, slave address (in decimal)
		self.pch = pch
		
		
	def init_gtk(self) :
		self.main = gtk.Window(gtk.WINDOW_TOPLEVEL)
		self.main.connect("delete_event", self.quit)
		self.main.connect("destroy", self.quit)
	
		self.main.set_size_request(800, 600)
	
		self.notebook = gtk.Notebook()
		
		t = gtk.Table(2,8)
		f = gtk.Frame()
		f.add(t)
		f.set_label("Температура")
		
		vbox = gtk.VBox()		
		vbox.pack_start(f)		

		hbox1 = gtk.HBox()
		self.push_labels = []
		l = gtk.Label("0 тонн") 
		self.push_labels.append(l)
		hbox1.pack_start(l)		
		
		l = gtk.Label("(0)") 
		self.push_labels.append(l)
		hbox1.pack_start(l)		

		l = gtk.Label("-") 
		self.push_labels.append(l)
		hbox1.pack_start(l)		
		
		l = gtk.Label("-") 
		self.push_labels.append(l)
		hbox1.pack_start(l)		

		l = gtk.Label("-") 
		self.push_labels.append(l)
		hbox1.pack_start(l)		


		
		f = gtk.Frame()
		f.add(hbox1)
		f.set_label("Давление")
		vbox.pack_start(f)				
		
		hbox = gtk.HBox()

		

		img = gtk.Image()
		img.set_from_file('press.svg')		
		vbox.pack_start(img)
		hbox.pack_start(vbox)		
		self.notebook.append_page(	hbox,gtk.Label("Состояние")	)
	
		self.temp_labels = []
		for i in range(8) :
			l = gtk.Label("Зона %s:"%(i+1))
			t.attach(l,0,1,i,i+1)

			l = gtk.Label("0")
			t.attach(l,1,2,i,i+1)
			self.temp_labels.append(l)
			
			l = gtk.Label("0")
			t.attach(l,2,3,i,i+1)
			self.temp_labels.append(l)
			
			l = gtk.Label("(0)")
			t.attach(l,3,4,i,i+1)
			self.temp_labels.append(l)

			l = gtk.Label("_")
			t.attach(l,4,5,i,i+1)
			self.temp_labels.append(l)

			l = gtk.Label("_")
			t.attach(l,6,7,i,i+1)
			self.temp_labels.append(l)
			
			
		vbox = gtk.VBox()		

		b = gtk.Button("Пуск")
		b.connect("clicked", self.start)
		vbox.pack_start(b)				
		self.cycle_enable = b

		b = gtk.Button("Стоп")
		b.connect("clicked", self.stop)
		vbox.pack_start(b)				
		self.stop = b

		b = gtk.ToggleButton("Расжать")
		b.connect("clicked", self.release_click)
		vbox.pack_start(b)				
		self.release_button = b

		b = gtk.Button("Тест")
		b.connect("clicked", self.test)
		vbox.pack_start(b)				
		self.test_button = b
		
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

	
			#self.notebook.append_page(t,gtk.Label("Зона %s"%n))
									

		####	Test panel		####

		self.main.add(self.notebook)
		self.main.show_all()				
	
	def release_click(self, *arg) :
		self.push.release(self.release_button.get_active())


	def quit(self, *arg) :
		self.off()
#		self.conf.write(open("press.ini","w"))
		subprocess.Popen(["halrun", "-U"])
		gtk.main_quit()
		return gtk.FALSE	

	def stop(self, *arg) :
		self.running = False
		self.press_prog == "stop" 		
		self.off()		

	def off(self, *arg) :
		for z in self.zones :
			z.heater = False
			z.cooler = False
		self.push.freq = 0	
		self.pch.write_register(50009,0,0)				
		self.mu110.write_register(0x62, 0, 0) # Registernumber, value, number of decimals for storage
		self.mu110.write_register(0x61, 0, 0) # Registernumber, value, number of decimals for storage
		self.state = [False for i in range(32)]
		self.push.pull = False
		self.push.push = False		
		
	def start(self, *arg) :
		self.running = True
		self.cycle = 0
		self.start_time = time()
		self.press_prog = "prog"
		gobject.timeout_add(press_update_int, self.run) # call every min		
		gobject.timeout_add(10000, self.graph) # call every min		

	
	
	def log(self) :
		l = ""	
		for z in self.zones :
			l +="%.1f,	" % z.get_temp(0)
			l +="%.1f,	" % z.get_temp(1)
		l += "%.1f,	" % self.push.get_fb()
		self.log_file.write(strftime("%Y-%m-%d %H:%M:%S,	")+l + "\n")
		self.log_file.flush()
		return True
		
		
	def graph(self) :
		for i in range(4):
			z = self.zones[i]
			self.graph_list[i].append(z.get_temp())
		self.graph_list[-1].append(time())
		self.graph_list = [l[-400:] for l in self.graph_list]

		if time()-self.last_graph_update > 60 :
			self.last_graph_update = time()
								
	

	def run(self) :
		print self
		if not self.running :
			return False
		if self.push.freq > 0  :
			# operate pusher
			self.push.update(self.cycle)
		else :
			if self.press_prog == "prog"  :	
				self.cycle = time() - self.start_time
				c = int(self.cycle)
				self.cycle_label.set_text("%02d:%02d:%02d"%(c/3600,c/60%60,c%60) )
				done = True
				self.push.update(self.cycle)
				for z in self.zones :
					z.update(self.cycle)
					done = done and z.done
				if done :
					self.press_prog = "release"
					self.push.release(True)
			if self.press_prog == "release" :
				if self.push.releasing == "done" :
					self.press_prog = "move"
			if self.press_prog == "move" :
				sleep(1)			
				self.move(self.cycle_move)
				sleep(3)			
				self.push.release(False)
				self.press_prog = "done"

			if self.press_prog == "done" :
					self.cycle_count += 1	
					self.cycle_num.set_text("%s"%self.cycle_count)
					self.cycle = 0
					self.start_time = time()
					self.press_prog = "prog"
		return True	
			
			
	def off_update(self) :
		for z in self.zones :
				z.off_update()
		self.push.off_update()

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

	
	def update_labels(self):
	
		if self.label_update_timer < time() :
			self.label_update_timer = time() + 0.5
			
			i = 0
			for z in self.zones:
				self.temp_labels[i].set_text("%.1f"%self.sens[z.t_n])
				self.temp_labels[i+1].set_text("%.1f"%self.sens[z.t1_n])
				self.temp_labels[i+2].set_text("(%.1f)"%z.get_command(self.cycle))
				self.temp_labels[i+3].set_text("H" if z.heater else "-")
				self.temp_labels[i+4].set_text("O" if z.cooler else "-")

				
				i += 5
			self.push_labels[0].set_text("%.3f тонн"%self.push.get_fb())
			self.push_labels[1].set_text("(%.1f)"%self.push.get_command(self.cycle))
			
			self.push_labels[2].set_text("\\/" if self.push.push else "--")
			self.push_labels[3].set_text("/\\" if self.push.pull else "--")
			self.push_labels[4].set_text("%.1fHz" % (self.push.freq/PCH_K) )
			

	def read_sens(self, c) :
		
		mv_ = c/8
		mv = self.mv110[mv_]
		n_ = c%8*6
		v = mv.read_register(n_+1)
		m = mv.read_register(n_+0)
		self.sens[c] = float(v)/(10**m)	
		return self.sens[c]


	def write_m110(self, state) :
		if self.state != state :
 			t, t1 = 0,0
			for i in range(16):
				t |= (1<<i)*state[i]
				t1 |= (1<<i)*state[i+16]
			b = False			
			while not b	:
				try : 
					self.mu110.write_register(0x62, t, 0) # Registernumber, value, number of decimals for storage
					b = True
				except :
					b = False	
			b = False			
			while not b	:
				try : 
					self.mu110.write_register(0x61, t1, 0) # Registernumber, value, number of decimals for storage
					b = True
				except :
					b = False	
		self.state = state					

	

	def update_rs(self, off=False) :
		self.push.release()

		state = [False for i in range(32)]
		
		if (self.push.freq > 0) : 
			# operate pusher
			for z in self.zones :
				state[z.heater_n] = False
 				state[z.cooler_n] = False
						
		else :		
			for z in self.zones :
 				state[z.heater_n] = z.heater
 				state[z.cooler_n] = z.cooler

		state[self.push.push_n] = self.push.push
		state[self.push.pull_n] = self.push.pull
		self.write_m110(state)

		if self.push.freq != self.freq_state :
			b = False
			while not b : 
				try: 
					self.push.pch.write_register(50009,self.push.freq,0)
					self.freq_state = self.push.freq
					b = True
				except: 
					b = False

		if (self.push.freq > 0) : 
			# operate pusher
			self.read_sens(self.push.sens_n)
		else :	
			self.read_sens(self.rs_read_counter % 17)
			self.rs_read_counter += 1	

		# update labels
		self.update_labels()
			
		return True
						
	
	
	def operate(self):
		pass


if __name__ == "__main__":
	press = Press()
	gtk.main()

