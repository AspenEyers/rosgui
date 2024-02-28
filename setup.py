from setuptools import setup, find_packages

with open('README.md', 'r') as f:
    long_description = f.read()

setup(
    name='rosgui',
    version='0.1.0',
    packages=find_packages(),
    install_requires=[
        # Dependencies, e.g., 'numpy', 'pandas'
    ],
    python_requires='>=3.6',
    description='A GUI application for ROS',
    long_description=long_description,
    long_description_content_type='text/markdown',
    url='https://github.com/yourusername/rosgui',
    author='Your Name',
    author_email='your.email@example.com',
    classifiers=[
        'Development Status :: 3 - Alpha',
        'Intended Audience :: Developers',
        'Topic :: Software Development :: Build Tools',
        'License :: OSI Approved :: MIT License',
        'Programming Language :: Python :: 3',
    ],
    keywords='ROS GUI robotics',
    entry_points={
        'console_scripts': [
            'rosgui=rosgui:main_function',  # Adjust as per your package structure and entry function
        ],
    },
)