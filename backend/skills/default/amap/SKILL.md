---
name: 高德地图
description: 高德地图服务 - 地理编码、路径规划、POI搜索、天气查询、距离测量等地图相关功能
category: map
---

# 高德地图 Skill

当用户需要地图、地理位置、路径规划、天气查询、POI搜索等地图相关功能时，使用以下工具。

> ⚠️ **重要提醒**: `call_tool()` 函数已经预注入到 Python 执行环境中，**直接调用即可**。
> **绝对不要**自己定义 `call_tool` 函数、mock 函数或用 subprocess/HTTP 模拟调用！

> **重要**: 所有坐标格式为 `经度,纬度`（例如 `116.397428,39.90923`），使用高德坐标系。

## 地理编码

### maps_geo - 地址转坐标
将详细的结构化地址转换为经纬度坐标。支持对地标性名胜景区、建筑物名称解析为经纬度坐标。

```python
# 地址转坐标
result = call_tool('maps_geo', {
    'address': '北京市朝阳区阜通东大街6号',  # required: 待解析的结构化地址信息
    'city': '北京'  # optional: 指定查询的城市
})
```

### maps_regeocode - 坐标转地址
将一个高德经纬度坐标转换为行政区划地址信息。

```python
# 坐标转地址
result = call_tool('maps_regeocode', {
    'location': '116.397428,39.90923'  # required: 经纬度，格式：经度,纬度
})
```

## POI搜索

### maps_text_search - 关键词搜索POI
根据用户传入关键词，搜索出相关的POI（兴趣点）。

```python
# 关键词搜索POI
result = call_tool('maps_text_search', {
    'keywords': '西湖',     # required: 搜索关键词
    'city': '杭州',         # optional: 查询城市
    'types': '风景名胜'     # optional: POI类型，比如加油站、风景名胜
})
```

### maps_around_search - 周边搜索POI
根据用户传入关键词以及坐标，搜索出指定半径范围内的POI。

```python
# 周边搜索
result = call_tool('maps_around_search', {
    'location': '116.397428,39.90923',  # required: 中心点经纬度
    'keywords': '餐厅',                 # optional: 搜索关键词
    'radius': '1000'                    # optional: 搜索半径（米）
})
```

### maps_search_detail - POI详情查询
查询关键词搜索或周边搜索获取到的POI ID的详细信息。

```python
# 查询POI详细信息
result = call_tool('maps_search_detail', {
    'id': 'B0FFH2CKXE'  # required: 关键词搜索或周边搜索获取到的POI ID
})
```

## 路径规划

### maps_direction_driving - 驾车路径规划
规划以小客车、轿车通勤出行的方案。

```python
# 驾车路径规划
result = call_tool('maps_direction_driving', {
    'origin': '116.397428,39.90923',       # required: 出发点经纬度
    'destination': '120.153576,30.287459'   # required: 目的地经纬度
})
```

### maps_direction_walking - 步行路径规划
规划100km以内的步行通勤方案。

```python
# 步行路径规划
result = call_tool('maps_direction_walking', {
    'origin': '116.397428,39.90923',       # required: 出发点经纬度
    'destination': '116.407428,39.91923'   # required: 目的地经纬度
})
```

### maps_bicycling - 骑行路径规划
规划骑行通勤方案，最大支持500km。

```python
# 骑行路径规划
result = call_tool('maps_bicycling', {
    'origin': '116.397428,39.90923',       # required: 出发点经纬度
    'destination': '116.507428,39.92923'   # required: 目的地经纬度
})
```

### maps_direction_transit_integrated - 公交路径规划
规划综合各类公共交通（火车、公交、地铁）方式的通勤方案。跨城场景下必须传起点城市与终点城市。

```python
# 公交路径规划
result = call_tool('maps_direction_transit_integrated', {
    'origin': '116.397428,39.90923',       # required: 出发点经纬度
    'destination': '120.153576,30.287459',  # required: 目的地经纬度
    'city': '北京',                         # required: 起点城市
    'cityd': '杭州'                         # required: 终点城市
})
```

## 距离测量

### maps_distance - 距离测量
测量两个经纬度坐标之间的距离，支持驾车、步行以及球面距离测量。

```python
# 距离测量
result = call_tool('maps_distance', {
    'origins': '116.397428,39.90923',       # required: 起点经纬度（多个用竖线分隔：120,30|120,31）
    'destination': '120.153576,30.287459',  # required: 终点经纬度
    'type': '1'  # optional: 1=驾车距离, 0=直线距离, 3=步行距离
})
```

## 天气与定位

### maps_weather - 天气查询
根据城市名称或标准adcode查询天气信息。

```python
# 天气查询
result = call_tool('maps_weather', {
    'city': '杭州'  # required: 城市名称或adcode
})
```

### maps_ip_location - IP定位
根据IP地址定位所在位置。

```python
# IP定位
result = call_tool('maps_ip_location', {
    'ip': '114.247.50.2'  # required: IP地址
})
```

## 使用示例

### 查找附近餐厅
```python
# 1. 先通过地址获取坐标
geo = call_tool('maps_geo', {'address': '杭州市西湖区'})
# 2. 周边搜索餐厅
restaurants = call_tool('maps_around_search', {
    'location': geo['geocodes'][0]['location'],
    'keywords': '餐厅',
    'radius': '2000'
})
```

### 规划出行路线
```python
# 1. 获取起终点坐标
origin = call_tool('maps_geo', {'address': '北京天安门'})
dest = call_tool('maps_geo', {'address': '北京首都机场'})
# 2. 驾车路径规划
route = call_tool('maps_direction_driving', {
    'origin': origin['geocodes'][0]['location'],
    'destination': dest['geocodes'][0]['location']
})
```

