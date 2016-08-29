paper.install(window);
function draw_telescope(axis, flen) {
   var i=0; var j=0;
   var telrat = 4.15;
   var len = flen*view.size.width;
   var width = len/telrat;
   var segLengths = [0.167,0.192,0.218,0.256,0.167];
   var segWidths = [0.317,0.366,0.317];
   var p0 = new Point(axis.x-len/5,axis.y-width/2);
   var p1 = new Point(axis.x+4*len/5,axis.y+width/2);
   var outline = new Path.Rectangle(new Rectangle(p0,p1));
   outline.strokeColor = "black";
   outline.strokeWidth = 2;
   telescope = new Group();
   telescope.addChild(outline);
   var rec0 = outline.clone();
   rec0.strokeWidth = 1;
   var segment = new Group();
   segment.addChild(rec0);
   var tl = rec0.bounds.topLeft.clone(); br = rec0.bounds.bottomRight.clone()
   var tr = rec0.bounds.topRight.clone(); bl = rec0.bounds.bottomLeft.clone()
   var diag1 = new Path.Line(tl,br);
   diag1.strokeColor = '#555555';
   var diag2 = new Path.Line(tr,bl);
   diag2.strokeColor = '#555555';
   segment.addChild(diag1);
   segment.addChild(diag2);
   /* Now add segments */
   var xoffset = segLengths[0]*len;
   for (i = 1 ; i < segLengths.length ; i++) {
      var yoffset = 0;
      for (j = 0 ; j < segWidths.length ; j++) {
         var rect = segment.clone();
         rect.scale(segLengths[i], segWidths[j]);
         rect.position.x = p0.x + xoffset + segLengths[i]*len/2;
         rect.position.y = p0.y + yoffset + segWidths[j]*width/2;
         telescope.addChild(rect);
         yoffset += segWidths[j]*width;
      }
      xoffset += segLengths[i]*len;
   }
   segment.remove()
   return telescope;
}


function draw_dome (fdiameter, fheight, alt, az) {
   var rad = view.size.width*fdiameter/2;
   var height = fheight*view.size.width;
   var center = new Point(view.center.x, view.center.x);
   var NewtLength = rad*0.5;
   var NewtWidth = NewtLength*0.1;
   var cableInset = NewtLength*3/4;
   var cableHeight = rad*5/8;
   var cableX = view.center.x + Math.sqrt(rad*rad - cableHeight*cableHeight);
   var cableAngle = 75;
   var shutterWidth = 0.2; //units of radius

   var dome = new Path.Circle({
      center: center,
      radius: rad,
      strokeColor: 'black'
   });
   var ll = new Point(1,view.center.x); 
   var ur = new Point(view.size.width-2,view.center.x+rad+1);
   var rect = new Rectangle(ll, ur);
   var blk = new Path.Rectangle(rect);
   blk.fillColor = 'white';
   var ll1 = new Point(view.center.x-rad,view.center.x);
   var ur1 = new Point(view.center.x+rad,view.center.x+height);
   var rect = new Rectangle(ll1,ur1);
   var bot = new Path.Rectangle(rect);
   bot.strokeColor = 'black'; 

   var ll2 = new Point(view.center.x + rad - NewtLength,
                       view.center.x + NewtWidth/2);
   var ur2 = new Point(view.center.x + rad,
                       view.center.x - NewtWidth/2);
   var rect2 = new Rectangle(ll2, ur2);
   var platform = new Path.Rectangle(rect2);
   platform.strokeColor = 'black';
   platform.fillColor = 'black';
   var p1 = new Point(view.center.x + rad - cableInset,
                      view.center.x - NewtWidth/2);
   var p2 = new Point(cableX, view.center.x-cableHeight);
   var cable = new Path(p1,p2);
   cable.strokeColor = 'black';
   telescope = draw_telescope(center, 0.47);
   telescope.rotate(-alt, center);

   var newLayer = new Layer();
   var center2 = new Point(view.center.x, view.center.x + 1.8*rad);
   var dome2 = new Path.Circle({
      center: center2,
      radius: rad,
      strokeColor: 'black',
      /* clipMask: true,*/
   });

   var mask = new Path.Circle({
      center: center2,
      radius: rad+1,
      strokeColor: 'black',
      clipMask: true,
   });
   var ll3 = new Point(center2.x-shutterWidth*rad,
                       center2.y-shutterWidth*rad);
   var ur3 = new Point(center2.x+rad, center2.y+shutterWidth*rad);
   var rect3 = new Rectangle(ll3, ur3);
   var shutter = new Path.Rectangle(rect3);
   shutter.fillColor = 'black';
   var azDome = new Group([dome2,shutter]);
   azDome.rotate(az-90);
   return azDome;
}
