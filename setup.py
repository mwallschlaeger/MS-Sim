#!/usr/bin/env python

from distutils.core import setup
setup(name='ms-sim',
      version='0.1',
      description='ms-sim is a tool to simulate or imitate services by utilizing system resources and network traffic.',
      author='mwallschlaeger',
      author_email='marcel.wallschlaeger@tu-berlin.de',
      url='https://github.com/mwallschlaeger/ms-sim',
      scripts=['ms-yaml-build', 'ms-device-simulator'],
      packages=['network','network/raw_tcp','utilization','.','stress-ng','stress-ng/bindings'],
      package_dir={'stress-ng': 'stress-ng'},
      package_data={'stress-ng': ['stress-ng.so']},      
    )
