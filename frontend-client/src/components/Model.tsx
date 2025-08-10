
import { useGLTF } from '@react-three/drei'
import * as THREE from 'three'

export function Model(props: any) {
  const { nodes, materials } = useGLTF('/scene.gltf')
  return (
    <group {...props} dispose={null}>
      <group rotation={[-Math.PI / 2, 0, 0]}>
        <group rotation={[Math.PI / 2, 0, 0]}>
          <mesh
            castShadow
            receiveShadow
            geometry={(nodes.defaultMaterial as THREE.Mesh).geometry}
            material={materials.glass}
          />
          <mesh
            castShadow
            receiveShadow
            geometry={(nodes.defaultMaterial_1 as THREE.Mesh).geometry}
            material={materials.BOT2}
          />
          <mesh
            castShadow
            receiveShadow
            geometry={(nodes.defaultMaterial_2 as THREE.Mesh).geometry}
            material={materials.BOT1}
          />
        </group>
      </group>
    </group>
  )
}

useGLTF.preload('/scene.gltf')