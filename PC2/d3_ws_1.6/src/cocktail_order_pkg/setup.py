import os
from glob import glob
from setuptools import find_packages, setup

package_name = 'cocktail_order_pkg'
resource_files = glob('resource/*.*')
if os.path.exists('resource/.env'):
    resource_files.append('resource/.env')

setup(
    name=package_name,
    version='0.0.0',
    packages=find_packages(exclude=['test']),
    data_files=[
        ('share/ament_index/resource_index/packages',
            ['resource/' + package_name]),
        ('share/' + package_name, ['package.xml']),
        # resource 폴더 내의 단일 파일들 복사 (.env, beep.mp3 등)
        (os.path.join('share', package_name, 'resource'), resource_files),
        # Vector DB 폴더 복사
        (os.path.join('share', package_name, 'resource', 'cocktail_vector_db'), glob('resource/cocktail_vector_db/*')),
    ],
    install_requires=['setuptools'],
    zip_safe=True,
    maintainer='user',
    maintainer_email='user@todo.todo',
    description='Cocktail Order Manager using Action Server',
    license='TODO: License declaration',
    tests_require=['pytest'],
    entry_points={
        'console_scripts': [
            # 터미널에서 실행할 명령어 매핑 (ros2 run cocktail_order_pkg order_node)
            'order_node = cocktail_order_pkg.integrated_order_node:main',
            'build_db   = cocktail_order_pkg.build_db:main',
        ],
    },
)