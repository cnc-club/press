#!/usr/bin/env python
# -*- coding: utf-8 -*-
import serial
from time import sleep
import pygtk
import gtk
import gobject
import minimalmodbus







git@github.com:cnc-club/press.git

class Zone



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



class Press():
	def __init__(self):
		
		self.instrument = minimalmodbus.Instrument('/dev/ttyS0', 16) # port name, slave address (in decimal)
		self.instrument.serial.baudrate = 9600   # Baud
		self.instrument.serial.bytesize = 8
		self.instrument.serial.parity   = serial.PARITY_NONE
		self.instrument.serial.stopbits = 1
		self.instrument.serial.timeout  = 1.5   # seconds
		self.instrument.mode = minimalmodbus.MODE_ASCII 


		#Set the Glade file
		builder = gtk.Builder()
		builder.add_from_file("press.glade")
		self.swtable = builder.get_object("swtable")
		tab = self.swtable
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

		self.main = builder.get_object("MainWindow")
		self.main.connect("delete_event", self.quit)
		self.main.connect("destroy", self.quit)


		self.main.show_all()				
	
	def quit(self,a=None, b=None):
		self.off()
		gtk.main_quit()
		return gtk.FALSE	
		
		
	def press(self,b) :
		if self.press_on.get_active() and b!=self.press_on:
			if b.get_active():
				self.instrument.write_register(rele["p0"], 0, 0) # Registernumber, value, number of decimals for storage
				self.instrument.write_register(rele["p1"], 1000, 0) # Registernumber, value, number of decimals for storage
			else :
				self.instrument.write_register(rele["p1"], 0, 0) # Registernumber, value, number of decimals for storage
				self.instrument.write_register(rele["p0"], 1000, 0) # Registernumber, value, number of decimals for storage
		else :
				self.instrument.write_register(rele["p1"], 0, 0) # Registernumber, value, number of decimals for storage
				self.instrument.write_register(rele["p0"], 0, 0) # Registernumber, value, number of decimals for storage

	def off(self,a=0,b=0) :
		for i in range(32) :
			self.turn_off(i)
			
	def turn_on(self, n, v = 1000):
		self.instrument.write_register(n, v, 0) # Registernumber, value, number of decimals for storage
	def turn_off(self, n, v = 1000):
		self.instrument.write_register(n, 0, 0) # Registernumber, value, number of decimals for storage

	
    
	def toggle(self, b, k):
		if b.get_active():
			self.turn_on(k)
		else :
			self.turn_off(k)
		



#print self.instrument.read_register(97, 2) # Registernumber, value, number of decimals for storage
#self.instrument.write_register(97, 255, 1) # Registernumber, value, number of decimals for storage
#for i in range(200): 
#	self.instrument.write_register(97, i	, 0) # Registernumber, value, number of decimals for storage
#	sleep(0.2)
## Read temperature (PV = ProcessValue) ##
#for i in range (100) :
#	try:
#		temperature = self.instrument.read_register(1) # Registernumber, number of decimals
#
#		print temperature,i
#	except :
#		pass
## Change temperature setpoint (SP) ##
#NEW_TEMPERATURE = 95

if __name__ == "__main__":
	press = Press()
	gtk.main()

