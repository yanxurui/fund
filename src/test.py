from gevent import sleep
from gevent.pool import Pool

if __name__ == '__main__':
	def do_something(a):
		print(a)
		sleep(1)
		if a == 2:
			raise Exception('whats wrong')
		return a

	pool = Pool(2)
	for a in pool.imap(do_something, [1,2,3]):
	    pass
