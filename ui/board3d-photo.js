import * as T from './three.module.js';

// A depth-aware photo pass: only the setting behind the board goes out of focus.
// Temporary render targets are disposed immediately after each PNG capture.
export function photograph(renderer,scene,camera,canvas,{width=3840,height=2160,blur=0}={},draw=null){
 const gl=renderer.getContext(),limit=Math.min(gl.getParameter(gl.MAX_RENDERBUFFER_SIZE),renderer.capabilities.maxTextureSize);
 if(width>limit||height>limit)throw Error(ArenaI18n.t('4K export is unavailable on this graphics device.'));
 const oldSize=new T.Vector2();renderer.getSize(oldSize);const oldRatio=renderer.getPixelRatio(),aspect=camera.aspect,view=camera.view?{...camera.view}:null;
 let target,geometry,material;
 try{
  renderer.setDrawingBufferSize(width,height,1);camera.aspect=width/height;
  if(view?.enabled)camera.setViewOffset(width,height,0,view.offsetY/view.fullHeight*height,width,height);camera.updateProjectionMatrix();
  if(blur>0){
   target=new T.WebGLRenderTarget(width,height,{type:T.HalfFloatType,depthTexture:new T.DepthTexture(width,height)});
   renderer.setRenderTarget(target);renderer.render(scene,camera);renderer.setRenderTarget(null);
   const picture=draw?draw(true):target.texture;
   geometry=new T.PlaneGeometry(2,2);
   material=new T.ShaderMaterial({uniforms:{picture:{value:picture},depth:{value:target.depthTexture},pixel:{value:new T.Vector2(1/width,1/height)},near:{value:camera.near},far:{value:camera.far},focus:{value:camera.position.length()+5},amount:{value:blur}},vertexShader:'varying vec2 uvPhoto; void main(){uvPhoto=uv;gl_Position=vec4(position.xy,0.,1.);}',fragmentShader:`
    uniform sampler2D picture,depth;uniform vec2 pixel;uniform float near,far,focus,amount;varying vec2 uvPhoto;
    float distanceAt(vec2 at){float z=texture2D(depth,at).x;return near*far/(far-z*(far-near));}
    void main(){float d=distanceAt(uvPhoto);float radius=smoothstep(focus,focus+12.,d)*amount*10.;vec4 sum=texture2D(picture,uvPhoto);float weight=1.;
     for(int i=0;i<24;i++){float a=float(i)*2.399963;float r=sqrt((float(i)+.5)/24.)*radius;vec2 pos=uvPhoto+vec2(cos(a),sin(a))*r*pixel;float w=smoothstep(focus-1.,focus+1.,distanceAt(pos));sum+=texture2D(picture,pos)*w;weight+=w;}
     gl_FragColor=sum/weight;
     #include <tonemapping_fragment>
     #include <colorspace_fragment>
    }`});
   const quad=new T.Scene();quad.add(new T.Mesh(geometry,material));renderer.render(quad,new T.Camera());
  }else if(draw)draw(false);else renderer.render(scene,camera);
  return canvas.toDataURL('image/png');
 }finally{
  renderer.setRenderTarget(null);target?.dispose();geometry?.dispose();material?.dispose();renderer.setDrawingBufferSize(oldSize.x,oldSize.y,oldRatio);camera.aspect=aspect;
  if(view?.enabled)camera.setViewOffset(view.fullWidth,view.fullHeight,view.offsetX,view.offsetY,view.width,view.height);else camera.clearViewOffset();camera.updateProjectionMatrix();
  if(draw)draw(false);else renderer.render(scene,camera);
 }
}
