#!/usr/bin/env node
import 'source-map-support/register';
import * as cdk from 'aws-cdk-lib';
import { S3WireStack } from '../lib/s3-wire-stack';

const app = new cdk.App();

// Obtener parámetros de contexto (opcionales)
const domain = app.node.tryGetContext('domain');
const hostedZoneId = app.node.tryGetContext('hostedZoneId');
const hostedZoneName = app.node.tryGetContext('hostedZoneName');

new S3WireStack(app, 'S3WireStack', {
  env: {
    account: process.env.CDK_DEFAULT_ACCOUNT,
    region: process.env.CDK_DEFAULT_REGION,
  },
  description: 'S3-Wire: Sistema serverless de subida de archivos mediante links temporales',
  
  // Parámetros opcionales para configuración de dominio
  domain: domain,
  hostedZoneId: hostedZoneId,
  hostedZoneName: hostedZoneName,
});
