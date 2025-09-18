import React, { useEffect, useRef, useState } from 'react';
import * as THREE from 'three';
import { OrbitControls } from 'three/examples/jsm/controls/OrbitControls.js';
import { GLTFLoader } from 'three/examples/jsm/loaders/GLTFLoader.js';

type Props = {
  url?: string;
  showReach?: boolean;
  onReady?: () => void;
};

export default function ModelViewer({ url, showReach, onReady }: Props) {
  const mountRef = useRef<HTMLDivElement>(null);
  const [error, setError] = useState<string | null>(null);
  const reachRef = useRef<THREE.Mesh|null>(null);
  const sceneRef = useRef<THREE.Scene|null>(null);

  useEffect(() => {
    const mount = mountRef.current!;
    const scene = new THREE.Scene();
    sceneRef.current = scene;
    scene.background = new THREE.Color(0x0b1215);
    const camera = new THREE.PerspectiveCamera(60, mount.clientWidth / mount.clientHeight, 0.1, 1000);
    camera.position.set(2, 2, 2);
    const renderer = new THREE.WebGLRenderer({ antialias: true });
    renderer.setSize(mount.clientWidth, mount.clientHeight);
    mount.appendChild(renderer.domElement);
    const controls = new OrbitControls(camera, renderer.domElement);
    controls.enableDamping = true;

    const light = new THREE.HemisphereLight(0xffffff, 0x444444, 1.0);
    scene.add(light);

    function addReach() {
      const geom = new THREE.SphereGeometry(0.75, 32, 16);
      const mat = new THREE.MeshBasicMaterial({ color: 0x2a9d8f, transparent: true, opacity: 0.2 });
      const mesh = new THREE.Mesh(geom, mat);
      reachRef.current = mesh;
      scene.add(mesh);
    }

    function removeReach() {
      const reachMesh = reachRef.current;
      if (reachMesh) { scene.remove(reachMesh); reachMesh.geometry.dispose(); (reachMesh.material as any).dispose(); reachRef.current = null; }
    }

    let animId: number;
    const animate = () => {
      controls.update();
      renderer.render(scene, camera);
      animId = requestAnimationFrame(animate);
    };
    animate();

    let model: THREE.Object3D | null = null;
    if (url) {
      const loader = new GLTFLoader();
      loader.load(url, (gltf) => {
        model = gltf.scene;
        scene.add(gltf.scene);
        if (onReady) onReady();
      }, undefined, (e) => setError('Failed to load model'));
    }

    const onResize = () => {
      const w = mount.clientWidth, h = mount.clientHeight;
      renderer.setSize(w, h);
      camera.aspect = w / h;
      camera.updateProjectionMatrix();
    };
    window.addEventListener('resize', onResize);

    return () => {
      cancelAnimationFrame(animId);
      window.removeEventListener('resize', onResize);
      if (model) scene.remove(model);
      renderer.dispose();
      mount.removeChild(renderer.domElement);
    };
  }, [url]);

  useEffect(() => {
    const scene = sceneRef.current;
    if (!scene) return;
    const mesh = reachRef.current;
    if (showReach) {
      if (!mesh) {
        const geom = new THREE.SphereGeometry(0.75, 32, 16);
        const mat = new THREE.MeshBasicMaterial({ color: 0x2a9d8f, transparent: true, opacity: 0.2 });
        const m = new THREE.Mesh(geom, mat);
        reachRef.current = m;
        scene.add(m);
      }
    } else {
      if (mesh) { scene.remove(mesh); mesh.geometry.dispose(); (mesh.material as any).dispose(); reachRef.current = null; }
    }
  }, [showReach]);

  return (
    <div>
      {!url && <div role="alert" className="muted">No model available.</div>}
      <div ref={mountRef} style={{ width: '100%', height: 400 }} aria-label="3D Viewer" role="application" tabIndex={0} />
    </div>
  );
}
