function box(width, length, height) {
    return { surface: 2*(width*length + length*height + height*width)
           , volume: width * length * height
           , width, length, height
           }
}

function cube(side) {
    return box(side, side, side)
}

function cylinder(diameter, length) {
    let radius = diameter / 2
    return { surface: 2*Math.PI*radius*radius + length*Math.PI*diameter
           , volume: Math.PI*radius*radius * length
           , diameter, length, radius
           }
}

function sphere(diameter) {
    let radius = diameter / 2
    return { surface: 4 * Math.PI * radius*radius
           , volume: 4/3 * Math.PI * radius*radius*radius
           , diameter, radius
           }
}
