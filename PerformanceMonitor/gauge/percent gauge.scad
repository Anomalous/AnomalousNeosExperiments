START_ANGLE = 45;           // degrees
END_ANGLE = 45;             // degrees
MAJOR_DIVISIONS = 10;        // number of major divisions (5 = every 20%)
MINOR_DIVISIONS = 50;       // number of minor divisions (20 = every 5%), must be divisible by number of major divisions
MAJOR_TIC_SIZE = [8,2,15];
MINOR_TIC_SIZE = [5,1,15];
GAUGE_RADIUS = 50;
OUTER_RADIUS = 55;
RIM_HEIGHT = 12;
FONT = "Liberation Sans:style=Bold";
FONT_SIZE = 6;

module gaugeFaceNegative() {
    for(divIdx = [0:MINOR_DIVISIONS]) {
        angleStep = (360 - START_ANGLE - END_ANGLE) / MINOR_DIVISIONS;
        angle = START_ANGLE + (divIdx * angleStep);
        if(divIdx % (MINOR_DIVISIONS / MAJOR_DIVISIONS) == 0)
            rotate([0,0,angle]) translate([-GAUGE_RADIUS, 0, 0]) {
                translate([MAJOR_TIC_SIZE[0]/2, 0, 0]) cube(MAJOR_TIC_SIZE, center=true);
                txt = str(100 - divIdx * (100/MINOR_DIVISIONS));
                rotate([0,0,90]) translate([0,-MAJOR_TIC_SIZE[0] - 6,0]) 
                    rotate([0,0,-angle + 180]) translate([0,0,-5]) linear_extrude(height = MAJOR_TIC_SIZE[2]) 
                        text(text=txt, font=FONT, size=FONT_SIZE, halign="center", valign="center");
            }
            
        else
            rotate([0,0,angle]) translate([-GAUGE_RADIUS+MINOR_TIC_SIZE[0]/2, 0, 0]) cube(MINOR_TIC_SIZE, center=true);
    }
}

module gaugeFace() {
    difference() {
        cylinder(r=OUTER_RADIUS + 1, h=5, $fn=72);
        gaugeFaceNegative();
    }
}

module gaugeRim() {
    difference() {
        cylinder(r=OUTER_RADIUS + 5, h=RIM_HEIGHT, $fn=72);
        translate([0,0,1]) cylinder(r=OUTER_RADIUS, h=20, $fn=72);
    }
}

module gaugeGlass() {
    translate([0,0,RIM_HEIGHT-3]) cylinder(r=OUTER_RADIUS + 1, h=1, $fn=72);
}

gaugeFace();
gaugeRim();
color([1,1,1,0.25]) gaugeGlass();