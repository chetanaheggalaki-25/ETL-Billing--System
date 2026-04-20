import express from 'express';
import nodemailer from 'nodemailer';
import cors from 'cors';
import dotenv from 'dotenv';
import bcrypt from 'bcryptjs';
import jwt from 'jsonwebtoken';

dotenv.config();

const app = express();
app.use(cors());
app.use(express.json());

// In-memory data stores (Replace with DB for production)
const users = []; // { id, name, email, password }
const tempUsers = {}; // { email: { name, password, otp, expires } }
const signInOTPs = {}; // { email: { otp, expires } }

const transporter = nodemailer.createTransport({
  host: 'smtp.gmail.com',
  port: 465,
  secure: true,
  auth: {
    user: process.env.EMAIL_USER,
    pass: process.env.EMAIL_PASS,
  },
});

// Helper: Generate OTP
const generateOTP = () => Math.floor(100000 + Math.random() * 900000).toString();

// Middleware: Authenticate Token
const authenticateToken = (req, res, next) => {
  const authHeader = req.headers['authorization'];
  const token = authHeader && authHeader.split(' ')[1];

  if (!token) return res.status(401).json({ error: 'Access denied. No token provided.' });

  jwt.verify(token, process.env.JWT_SECRET, (err, user) => {
    if (err) return res.status(403).json({ error: 'Invalid or expired token.' });
    req.user = user;
    next();
  });
};

// Route: Sign Up - Initial Request
app.post('/api/signup', async (req, res) => {
  const { name, email, password } = req.body;

  // Validation
  if (!name || !email || !password) return res.status(400).json({ error: 'All fields are required' });
  if (users.find(u => u.email === email)) return res.status(400).json({ error: 'User already exists' });

  const otp = generateOTP();
  const expires = Date.now() + 10 * 60 * 1000; // 10 minutes

  // Hash password before storing temporarily
  const hashedPassword = await bcrypt.hash(password, 10);

  tempUsers[email] = { name, email, password: hashedPassword, otp, expires };

  const mailOptions = {
    from: `"IntelliBill Extract" <${process.env.EMAIL_USER}>`,
    to: email,
    subject: 'Verify Your Email - IntelliBill Extract',
    html: `
      <div style="font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif; padding: 40px; background: #f0f4f8; border-radius: 12px; max-width: 450px; margin: auto; border: 1px solid #e1e8ed;">
        <h2 style="color: #1a73e8; text-align: center; margin-bottom: 20px;">Verification Code</h2>
        <p style="color: #4a5568; font-size: 16px;">Hello <b>${name}</b>,</p>
        <p style="color: #4a5568; font-size: 16px;">Use the code below to complete your registration for <b>IntelliBill Extract</b>:</p>
        <div style="background: #ffffff; padding: 20px; text-align: center; font-size: 32px; font-weight: bold; color: #1a73e8; letter-spacing: 5px; border-radius: 8px; margin: 25px 0; border: 2px dashed #cbd5e0;">
          ${otp}
        </div>
        <p style="color: #718096; font-size: 14px; text-align: center;">This code expires in 10 minutes.</p>
        <hr style="border: 0; border-top: 1px solid #e1e8ed; margin: 30px 0;">
        <p style="color: #a0aec0; font-size: 11px; text-align: center;">&copy; 2026 IntelliBill Extract. All rights reserved.</p>
      </div>
    `,
  };

  try {
    await transporter.sendMail(mailOptions);
    res.status(200).json({ message: 'OTP sent to email. Please verify.' });
  } catch (error) {
    console.error('Email error:', error);
    res.status(500).json({ error: 'Failed to send OTP. Please check your email configuration.' });
  }
});

// Route: Sign Up - Verify OTP
app.post('/api/verify-signup', async (req, res) => {
  const { email, otp } = req.body;
  const tempUser = tempUsers[email];

  if (!tempUser) return res.status(400).json({ error: 'Registration expired. Please try again.' });
  if (tempUser.otp !== otp) return res.status(400).json({ error: 'Invalid OTP' });
  if (Date.now() > tempUser.expires) return res.status(400).json({ error: 'OTP expired' });

  // Add to permanent users
  const newUser = { id: users.length + 1, name: tempUser.name, email: tempUser.email, password: tempUser.password };
  users.push(newUser);
  delete tempUsers[email];

  // Generate Token
  const token = jwt.sign({ id: newUser.id, email: newUser.email, name: newUser.name }, process.env.JWT_SECRET, { expiresIn: '24h' });

  res.status(200).json({ message: 'Account created successfully', token, user: { name: newUser.name, email: newUser.email } });
});

// Route: Sign In - Initial Request
app.post('/api/signin', async (req, res) => {
  const { email, password } = req.body;

  const user = users.find(u => u.email === email);
  if (!user) return res.status(400).json({ error: 'Invalid email or password' });

  const isMatch = await bcrypt.compare(password, user.password);
  if (!isMatch) return res.status(400).json({ error: 'Invalid email or password' });

  const otp = generateOTP();
  const expires = Date.now() + 10 * 60 * 1000;

  signInOTPs[email] = { otp, expires };

  const mailOptions = {
    from: `"IntelliBill Extract" <${process.env.EMAIL_USER}>`,
    to: email,
    subject: 'Login Verification Code - IntelliBill Extract',
    html: `
      <div style="font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif; padding: 40px; background: #eef2f7; border-radius: 12px; max-width: 450px; margin: auto; border: 1px solid #cfd9e1;">
        <h2 style="color: #2b6cb0; text-align: center; margin-bottom: 20px;">Login Verification</h2>
        <p style="color: #4a5568; font-size: 16px;">Hello,</p>
        <p style="color: #4a5568; font-size: 16px;">One-time password for your <b>IntelliBill Extract</b> login:</p>
        <div style="background: #ffffff; padding: 20px; text-align: center; font-size: 32px; font-weight: bold; color: #2b6cb0; letter-spacing: 5px; border-radius: 8px; margin: 25px 0; border: 2px solid #2b6cb0;">
          ${otp}
        </div>
        <p style="color: #718096; font-size: 14px; text-align: center;">This code is valid for 10 minutes.</p>
        <hr style="border: 0; border-top: 1px solid #cfd9e1; margin: 30px 0;">
        <p style="color: #a0aec0; font-size: 11px; text-align: center;">If you didn't request this, ignore this email.</p>
      </div>
    `,
  };

  try {
    await transporter.sendMail(mailOptions);
    res.status(200).json({ message: 'OTP sent to email. Please verify login.' });
  } catch (error) {
    res.status(500).json({ error: 'Failed to send OTP.' });
  }
});

// Route: Sign In - Verify OTP
app.post('/api/verify-signin', (req, res) => {
  const { email, otp } = req.body;
  const store = signInOTPs[email];

  if (!store || store.otp !== otp) return res.status(400).json({ error: 'Invalid or expired OTP' });
  if (Date.now() > store.expires) return res.status(400).json({ error: 'OTP expired' });

  delete signInOTPs[email];

  const user = users.find(u => u.email === email);
  const token = jwt.sign({ id: user.id, email: user.email, name: user.name }, process.env.JWT_SECRET, { expiresIn: '24h' });

  res.status(200).json({ message: 'Logged in successfully', token, user: { name: user.name, email: user.email } });
});

// Route: Protected Dashboard Info
app.get('/api/me', authenticateToken, (req, res) => {
  res.status(200).json({ user: req.user });
});

import { OAuth2Client } from 'google-auth-library';
const googleClient = new OAuth2Client(process.env.GOOGLE_CLIENT_ID);

// Route: Google - Verify Identity
app.post('/api/google-verify', async (req, res) => {
  const { credential } = req.body;
  
  try {
    // STRICT VERIFICATION: This checks the signature with Google's public keys
    const ticket = await googleClient.verifyIdToken({
        idToken: credential,
        audience: process.env.GOOGLE_CLIENT_ID
    });
    const payload = ticket.getPayload();
    
    if (!payload || !payload.email) throw new Error('Invalid Google account');

    // Issue a REAL JWT token mapped to this verified Google identity
    const token = jwt.sign(
      { id: payload.sub, email: payload.email, name: payload.name }, 
      process.env.JWT_SECRET, 
      { expiresIn: '24h' }
    );

    res.status(200).json({ 
      message: 'Google identity verified', 
      token, 
      user: { name: payload.name, email: payload.email } 
    });
  } catch (err) {
    console.error('Google Auth Error:', err);
    res.status(400).json({ error: 'Verification failed' });
  }
});

const PORT = process.env.PORT || 3001;
app.listen(PORT, () => {
  console.log(`Auth server running on port ${PORT}`);
});
