import { Mesh } from 'three';
import { ForwardRefComponent, NamedArrayTuple } from '../helpers/ts-utils';
import { ThreeElements } from '@react-three/fiber';
export type RoundedBoxProps = {
    args?: NamedArrayTuple<(width?: number, height?: number, depth?: number) => void>;
    radius?: number;
    smoothness?: number;
    bevelSegments?: number;
    steps?: number;
    creaseAngle?: number;
} & Omit<ThreeElements['mesh'], 'ref' | 'args'>;
export declare const RoundedBox: ForwardRefComponent<RoundedBoxProps, Mesh>;
