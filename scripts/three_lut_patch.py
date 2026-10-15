"""Engine Arena's small, reproducible Three.js r186.1 lifetime correction."""


def patch_lut(text):
    start = text.index('let lut = null;\n\nfunction getDFGLUT()')
    end = text.index('\n/**', start)
    text = text[:start] + '''// Engine Arena: each renderer owns its LUT. A shared texture's dispose listeners
// otherwise retain every retired WebGL context during long tournament sessions.
function createDFGLUT() {

\tconst lut = new DataTexture( DATA, 16, 16, RGFormat, HalfFloatType );
\tlut.name = 'DFG_LUT';
\tlut.minFilter = LinearFilter;
\tlut.magFilter = LinearFilter;
\tlut.wrapS = ClampToEdgeWrapping;
\tlut.wrapT = ClampToEdgeWrapping;
\tlut.generateMipmaps = false;
\tlut.needsUpdate = true;

\treturn lut;

}
''' + text[end:]
    changes = {
        '\t\tlet _alpha;': '\t\tlet _alpha, dfgLUT = null;',
        "\t\t\tcanvas.removeEventListener( 'webglcontextcreationerror', onContextCreationError, false );\n\n\t\t\tbackground.dispose();": "\t\t\tcanvas.removeEventListener( 'webglcontextcreationerror', onContextCreationError, false );\n\n\t\t\t// Dispose while this renderer's texture properties are still available.\n\t\t\tif ( dfgLUT !== null ) { dfgLUT.dispose(); dfgLUT = null; }\n\n\t\t\tbackground.dispose();",
        'm_uniforms.dfgLUT.value = getDFGLUT();': 'm_uniforms.dfgLUT.value = dfgLUT ??= createDFGLUT();',
    }
    for old, new in changes.items():
        assert text.count(old) == 1, 'Three.js source changed; review the lifetime patch'
        text = text.replace(old, new)
    return text
