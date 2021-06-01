from setuptools import setup
setup(name="flaskapp",
      packages=['flaskapp'],
      version='1',
      package_data={'':['static/*']},
      include_package_data=True,
      install_requires=['requests','pandas','selenium','webdriver_manager','openpyxl','Xlsxwriter'],
      )
