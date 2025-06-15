import os
from setuptools import setup, find_packages

try:
    with open(os.path.join(os.path.dirname(__file__), 'README.md'), encoding='utf-8') as f:
        long_description = f.read()
except:
    long_description = ''

setup(
    name='pretix-pwyc',
    version='0.0.9',
    description='Pay What You Can plugin for pretix',
    long_description=long_description,
    url='https://github.com/pietervanboheemen/pretix-pwyc',
    author='Pieter van Boheemen',
    author_email='mail@pietervanboheemen.nl',
    license='Apache Software License',
    classifiers=[
        'Development Status :: 4 - Beta',
        'Intended Audience :: Developers',
        'Intended Audience :: Other Audience',
        'License :: OSI Approved :: Apache Software License',
        'Programming Language :: Python :: 3.8',
        'Programming Language :: Python :: 3.9',
        'Programming Language :: Python :: 3.10',
        'Framework :: Django :: 3.2',
    ],
    packages=find_packages(exclude=['tests', 'tests.*']),
    install_requires=[],
    package_data={
        'pretix_pwyc': [
            'templates/pretix_pwyc/*.html',
            'static/pretix_pwyc/css/*.css',
            'static/pretix_pwyc/js/*.js',
            'locale/*/LC_MESSAGES/*.po',
            'locale/*/LC_MESSAGES/*.mo',
        ],
    },
    entry_points="""
        [pretix.plugin]
        pretix_pwyc=pretix_pwyc:PluginApp
    """,
)
