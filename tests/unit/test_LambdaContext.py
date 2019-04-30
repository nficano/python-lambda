from aws_lambda.helpers import LambdaContext
import time
import unittest

class TestLambdaContext(unittest.TestCase):

	def test_get_remaining_time_in_millis(self):
		context = LambdaContext('function_name', 2000)
		time.sleep(.5)
		self.assertTrue(context.get_remaining_time_in_millis() < 2000000)


if __name__ == '__main__':
	unittest.main()