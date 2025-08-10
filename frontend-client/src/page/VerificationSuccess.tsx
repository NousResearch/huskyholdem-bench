import React from 'react';
import { Link } from 'react-router-dom';
import CyberPunkButton from '../components/CyberPunkButton';
import './VerificationSuccess.css';

const VerificationSuccess: React.FC = () => {
    return (
        <div className="verification-container">
            <div className="verification-box">
                <h1 className="verification-title">
                    HUSKY<span className="title-accent">♠</span> HOLD'EM
                </h1>
                <h2 className="verification-header">Verification Successful!</h2>
                <p className="verification-text">
                    Your email has been confirmed. You can now log in and access all the features of the tournament.
                </p>
                <Link to="/login" style={{ textDecoration: 'none' }}>
                    <CyberPunkButton text="Proceed to Login" />
                </Link>
            </div>
        </div>
    );
};

export default VerificationSuccess;
