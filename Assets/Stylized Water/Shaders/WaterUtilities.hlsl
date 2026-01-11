#ifndef WATER_UTILITIES_INCLUDED
#define WATER_UTILITIES_INCLUDED

// DEFINES.
#define PI (3.1415926536)

// Returns a simple waveform (to be used as a height offset) from the input wave parameters.
float SimpleWave(float2 position, float2 direction, float wavelength, float amplitude, float speed)
{
    float x = PI * dot(position, direction) / wavelength;
    float phase = speed * _Time.y;
    return amplitude * sin(x + phase);
}

// Pans the input uv in the given direction and speed.
float2 Panner(float2 uv, float2 direction, float speed)
{
    return uv + normalize(direction) * speed * _Time.y;
}

// Unpacks a normal from a texture sample (URP version)
float3 UnpackNormalURP(float4 packedNormal)
{
    #if defined(UNITY_NO_DXT5nm)
        return packedNormal.xyz * 2.0 - 1.0;
    #else
        // DXT5nm format
        float3 normal;
        normal.xy = packedNormal.ag * 2.0 - 1.0;
        normal.z = sqrt(1.0 - saturate(dot(normal.xy, normal.xy)));
        return normal;
    #endif
}

// Tiles a texture in an interesting wave-like way.
// Inspired by the function of the same name in Unreal Engine.
float3 MotionFourWayChaos(TEXTURE2D_PARAM(tex, samplerTex), float2 uv, float speed, bool unpackNormal)
{
    float2 uv1 = Panner(uv + float2(0.000, 0.000), float2( 0.1,  0.1), speed);
    float2 uv2 = Panner(uv + float2(0.418, 0.355), float2(-0.1, -0.1), speed);
    float2 uv3 = Panner(uv + float2(0.865, 0.148), float2(-0.1,  0.1), speed);
    float2 uv4 = Panner(uv + float2(0.651, 0.752), float2( 0.1, -0.1), speed);

    float3 sample1;
    float3 sample2;
    float3 sample3;
    float3 sample4;

    if (unpackNormal)
    {
        sample1 = UnpackNormalURP(SAMPLE_TEXTURE2D(tex, samplerTex, uv1));
        sample2 = UnpackNormalURP(SAMPLE_TEXTURE2D(tex, samplerTex, uv2));
        sample3 = UnpackNormalURP(SAMPLE_TEXTURE2D(tex, samplerTex, uv3));
        sample4 = UnpackNormalURP(SAMPLE_TEXTURE2D(tex, samplerTex, uv4));

        return normalize(sample1 + sample2 + sample3 + sample4);
    }
    else
    {
        sample1 = SAMPLE_TEXTURE2D(tex, samplerTex, uv1).rgb;
        sample2 = SAMPLE_TEXTURE2D(tex, samplerTex, uv2).rgb;
        sample3 = SAMPLE_TEXTURE2D(tex, samplerTex, uv3).rgb;
        sample4 = SAMPLE_TEXTURE2D(tex, samplerTex, uv4).rgb;

        return (sample1 + sample2 + sample3 + sample4) / 4.0;
    }
}

float3 MotionFourWaySparkle(TEXTURE2D_PARAM(tex, samplerTex), float2 uv, float4 coordinateScale, float speed)
{
    float2 uv1 = Panner(uv * coordinateScale.x, float2( 0.1,  0.1), speed);
    float2 uv2 = Panner(uv * coordinateScale.y, float2(-0.1, -0.1), speed);
    float2 uv3 = Panner(uv * coordinateScale.z, float2(-0.1,  0.1), speed);
    float2 uv4 = Panner(uv * coordinateScale.w, float2( 0.1, -0.1), speed);

    float3 sample1 = UnpackNormalURP(SAMPLE_TEXTURE2D(tex, samplerTex, uv1));
    float3 sample2 = UnpackNormalURP(SAMPLE_TEXTURE2D(tex, samplerTex, uv2));
    float3 sample3 = UnpackNormalURP(SAMPLE_TEXTURE2D(tex, samplerTex, uv3));
    float3 sample4 = UnpackNormalURP(SAMPLE_TEXTURE2D(tex, samplerTex, uv4));

    float3 normalA = float3(sample1.x, sample2.y, 1);
    float3 normalB = float3(sample3.x, sample4.y, 1);
    
    return normalize(float3((normalA + normalB).xy, (normalA * normalB).z));
}

#endif  // WATER_UTILITIES_INCLUDED
