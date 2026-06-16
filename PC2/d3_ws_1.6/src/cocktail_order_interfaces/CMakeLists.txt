cmake_minimum_required(VERSION 3.8)
project(cocktail_order_interfaces)

if(CMAKE_COMPILER_IS_GNUCXX OR CMAKE_CXX_COMPILER_ID MATCHES "Clang")
  add_compile_options(-Wall -Wextra -Wpedantic)
endif()

# 의존성 패키지 찾기
find_package(ament_cmake REQUIRED)
find_package(rosidl_default_generators REQUIRED)
find_package(action_msgs REQUIRED)

# 액션 파일 빌드 명령
rosidl_generate_interfaces(${PROJECT_NAME}
  "action/CocktailOrder.action"
  "srv/TriggerCleanup.srv"
  DEPENDENCIES action_msgs
)


ament_package()