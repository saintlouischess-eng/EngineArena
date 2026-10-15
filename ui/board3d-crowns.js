// Original red crown artwork, projected onto the carved wood rather than a floating label.
import * as T from './three.module.js';
export function crownTexture(){
 const canvas=document.createElement('canvas');canvas.width=canvas.height=512;
 const c=canvas.getContext('2d');c.strokeStyle='#bf282b';c.lineWidth=18;c.lineJoin='round';c.lineCap='round';
 c.beginPath();c.moveTo(170,360);c.bezierCurveTo(146,300,83,278,99,218);c.bezierCurveTo(118,163,187,173,207,220);c.stroke();
 c.beginPath();c.moveTo(342,360);c.bezierCurveTo(366,300,429,278,413,218);c.bezierCurveTo(394,163,325,173,305,220);c.stroke();
 c.beginPath();c.moveTo(223,359);c.bezierCurveTo(217,303,188,269,195,214);c.bezierCurveTo(201,153,239,148,256,149);c.bezierCurveTo(273,148,311,153,317,214);c.bezierCurveTo(324,269,295,303,289,359);c.stroke();
 c.beginPath();c.moveTo(256,148);c.lineTo(256,102);c.moveTo(236,120);c.lineTo(276,120);c.stroke();
 c.beginPath();c.roundRect(165,357,182,35,9);c.stroke();
 const texture=new T.CanvasTexture(canvas);texture.colorSpace=T.SRGBColorSpace;return texture;
}
export function crownGeometry(source,type){
 // Exported sculptures are Y-up, with the knight facing -X. The crown sits
 // on its forehead; the rook's mark is inside the recessed turret top.
 const patch=type==='n'?{x:-.025,z:0,w:.19,h:.19}:{x:0,z:0,w:.24,h:.24};
 const probe=new T.Mesh(source.geometry,new T.MeshBasicMaterial());probe.updateMatrixWorld();
 const ray=new T.Raycaster(),positions=[],uv=[],indices=[],steps=12;
 for(let j=0;j<=steps;j++)for(let i=0;i<=steps;i++){
  // Crop away transparent canvas borders so the projected patch never
  // bridges from the narrow forehead down to the base of the knight.
  const u=.15+.70*i/steps,v=.17+.64*j/steps;
  const x=patch.x+(v-.5)*patch.h,z=patch.z+(u-.5)*patch.w;
  ray.set(new T.Vector3(x,2,z),new T.Vector3(0,-1,0));const hit=ray.intersectObject(probe,false)[0];
  if(!hit||hit.point.y<.9){probe.material.dispose();throw Error('Crown stamp misses the sculpture top')}
  positions.push(x,hit.point.y+.0007,z);
  // Keep the accepted knight artwork, size and orientation fixed to its head.
  // Only the rook's turret stamp reads upright from its owner's side.
  if(type==='n')uv.push(u,v);
  else{
   const dx=(x-patch.x)/patch.w,dz=(z-patch.z)/patch.h;
   uv.push(.5+1.15*dx,.5-1.15*dz);
  }
 }
 for(let j=0;j<steps;j++)for(let i=0;i<steps;i++){const a=j*(steps+1)+i,b=a+1,d=a+steps+1;indices.push(a,b,d,b,d+1,d)}
 probe.material.dispose();const geometry=new T.BufferGeometry();geometry.setAttribute('position',new T.Float32BufferAttribute(positions,3));geometry.setAttribute('uv',new T.Float32BufferAttribute(uv,2));geometry.setIndex(indices);geometry.computeVertexNormals();return geometry;
}
