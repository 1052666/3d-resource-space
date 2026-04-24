import math


def normalize(v):
    length = math.sqrt(v[0] ** 2 + v[1] ** 2 + v[2] ** 2)
    if length == 0:
        raise ValueError("zero vector cannot be normalized")
    return (v[0] / length, v[1] / length, v[2] / length)


def point_to_line_distance(point, line_point, direction):
    """点到无限直线的距离。direction 必须是单位向量。"""
    vx = point[0] - line_point[0]
    vy = point[1] - line_point[1]
    vz = point[2] - line_point[2]
    t = vx * direction[0] + vy * direction[1] + vz * direction[2]
    cx = line_point[0] + t * direction[0]
    cy = line_point[1] + t * direction[1]
    cz = line_point[2] + t * direction[2]
    dx = point[0] - cx
    dy = point[1] - cy
    dz = point[2] - cz
    return math.sqrt(dx * dx + dy * dy + dz * dz)


def query_projection(spheres, source_pos, target_pos, cylinder_radius, filter_mode):
    """查询单个投影匹配的资源球。返回 [(sphere_dict, match_type), ...]。"""
    direction = normalize((
        target_pos[0] - source_pos[0],
        target_pos[1] - source_pos[1],
        target_pos[2] - source_pos[2],
    ))

    results = []
    for sphere in spheres:
        sphere_pos = (sphere["calculated_x"], sphere["calculated_y"], sphere["calculated_z"])
        dist = point_to_line_distance(sphere_pos, source_pos, direction)
        sr = sphere["radius"]

        is_intersect = dist <= cylinder_radius + sr
        is_contain = cylinder_radius > sr and dist <= cylinder_radius - sr

        matched = False
        match_type = None
        if filter_mode == "intersect" and is_intersect:
            matched = True
            match_type = "intersect"
        elif filter_mode == "contain" and is_contain:
            matched = True
            match_type = "contain"
        elif filter_mode == "both" and (is_intersect or is_contain):
            matched = True
            match_type = "contain" if is_contain else "intersect"

        if matched:
            results.append((sphere, match_type))

    return results
