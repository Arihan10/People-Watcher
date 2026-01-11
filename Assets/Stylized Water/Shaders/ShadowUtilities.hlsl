#ifndef SHADOW_UTILITIES_INCLUDED
#define SHADOW_UTILITIES_INCLUDED

#include "Packages/com.unity.render-pipelines.universal/ShaderLibrary/Shadows.hlsl"

// Returns light visibility using URP's shadow system.
// Returns 1.0 if fully lit, 0.0 if fully in shadow.
float GetURPMainLightShadow(float3 positionWS, float maxDistance)
{
    // Calculate the distance from the camera.
    float distFromCam = length(positionWS - _WorldSpaceCameraPos.xyz);

    // If we are beyond the edge of the shadow map, return 1.0 (no shadow).
    if (distFromCam > maxDistance)
    {
        return 1.0;
    }

    // Get shadow coordinates for URP
    float4 shadowCoord = TransformWorldToShadowCoord(positionWS);
    
    // Sample the shadow map using URP's function
    Light mainLight = GetMainLight(shadowCoord);
    
    return mainLight.shadowAttenuation;
}

#endif  // SHADOW_UTILITIES_INCLUDED
