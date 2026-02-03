---
name: 路径规划技能
description: 帮助用户去规划相关路径或者搜索当地天气的技能
---
maps_regeocode
将一个高德经纬度坐标转换为行政区划地址信息：
# gaode/maps_regeocode-start #
call_tool('maps_regeocode', {location:This Is A String})
# gaode/maps_regeocode-end #


maps_geo:
将详细的结构化地址转换为经纬度坐标。支持对地标性名胜景区、建筑物名称解析为经纬度坐标：
# gaode/maps_geo-start #
call_tool('maps_geo', {address:This Is A String,city:This Is A String})
# gaode/maps_geo-end #


maps_weather:
根据城市名称或者标准adcode查询指定城市的天气：
# gaode/maps_weather-start #
call_tool('maps_weather', {city:This Is A String})
# gaode/maps_weather-end #

maps_search_detail:
查询关键词搜或者周边搜获取到的POI ID的详细信息：
# gaode/maps_search_detail-start #
call_tool('maps_search_detail', {id:This Is A String})
# gaode/maps_search_detail-end #

maps_direction_driving:
驾车路径规划 API 可以根据用户起终点经纬度坐标规划以小客车、轿车通勤出行的方案，并且返回通勤方案的数据。
# gaode/maps_direction_driving-start #
call_tool('maps_direction_driving', {origin:This Is A String, destination:This Is A String})
# gaode/maps_direction_driving-end #

maps_distance
距离测量 API 可以测量两个经纬度坐标之间的距离,支持驾车、步行以及球面距离测量
# gaode/maps_distance-start #
call_tool('maps_distance', {origin:This Is A String, destination:This Is A String}, type:int 1表示驾车距离测量 3表示步行距离测量)
# gaode/maps_distance-end #