import { ApiProperty, ApiPropertyOptional } from "@nestjs/swagger";

export class PricingIdrDto {
  @ApiProperty({ example: "76800", description: "FOB unit value in IDR" })
  fobUnit!: string;

  @ApiProperty({ example: "38400000", description: "FOB total value in IDR" })
  fobTotal!: string;

  @ApiProperty({ example: "38404800", description: "CFR total value in IDR" })
  cfrTotal!: string;

  @ApiProperty({ example: "38475200", description: "CIF total value in IDR" })
  cifTotal!: string;

  @ApiProperty({ example: "76950", description: "CIF price per unit in IDR" })
  perUnitCIF!: string;
}

export class PricingResponseDto {
  @ApiProperty({ example: "4.00", description: "FOB price per unit (USD)" })
  fobUnit!: string;

  @ApiProperty({ example: "2000.00", description: "FOB total value (USD)" })
  fobTotal!: string;

  @ApiProperty({
    example: "2000.30",
    description: "CFR total — FOB + ocean freight",
  })
  cfrTotal!: string;

  @ApiProperty({
    example: "4.40",
    description: "Cargo insurance premium (USD)",
  })
  insuranceAmount!: string;

  @ApiProperty({
    example: "2004.70",
    description: "CIF total — CFR + insurance",
  })
  cifTotal!: string;

  @ApiProperty({ example: "4.0094", description: "CIF price per unit (USD)" })
  perUnitCIF!: string;

  @ApiProperty({ type: PricingIdrDto })
  idr!: PricingIdrDto;

  @ApiPropertyOptional({
    nullable: true,
    description: "Benchmark unit value from trade data (null if unavailable)",
  })
  benchmarkUnitValue!: string | null;

  @ApiPropertyOptional({
    nullable: true,
    description: "Warning if price is below benchmark or below HPP",
  })
  pricingWarning!: string | null;

  @ApiProperty({
    example: "0.23%",
    description: "Estimated gross margin above HPP",
  })
  marginEstimate!: string;

  @ApiProperty({
    example: 16000,
    description: "Exchange rate used for IDR conversion",
  })
  exchangeRate!: number;
}

export class FraudFlagDto {
  @ApiProperty({ example: "overpayment_scam" })
  id!: string;

  @ApiProperty({
    example: "Permintaan kelebihan bayar yang harus dikembalikan.",
  })
  description!: string;

  @ApiProperty({ example: "HIGH", enum: ["LOW", "MEDIUM", "HIGH", "CRITICAL"] })
  severity!: string;

  @ApiProperty({
    example: "PAYMENT",
    enum: ["PAYMENT", "IDENTITY", "CONTRACT", "LOGISTICS"],
  })
  category!: string;

  @ApiProperty({ example: "ICC red flag catalogue" })
  referenceStandard!: string;

  @ApiProperty({ example: "overpaid" })
  matchedText!: string;
}

export class FraudScanResponseDto {
  @ApiProperty({ example: "RED", enum: ["GREEN", "YELLOW", "RED"] })
  riskLevel!: string;

  @ApiProperty({
    minimum: 0,
    maximum: 100,
    example: 45,
    description: "Higher = riskier",
  })
  riskScore!: number;

  @ApiProperty({ type: [FraudFlagDto] })
  flags!: FraudFlagDto[];

  @ApiProperty({
    example:
      "Jangan tanda tangani kontrak sebelum verifikasi lanjutan pembeli.",
  })
  recommendation!: string;
}

export class VerifyNibResponseDto {
  @ApiProperty({ example: "1234567890123" })
  nib!: string;

  @ApiProperty({ example: true })
  is_valid!: boolean;

  @ApiProperty({ example: "CV Kerajinan Nusantara" })
  business_name!: string;

  @ApiProperty({ example: "32904" })
  kbli!: string;

  @ApiProperty({
    example: "Industri Kerajinan yang Tidak Diklasifikasikan di Tempat Lain",
  })
  kbli_description!: string;

  @ApiProperty({
    example: "KECIL",
    enum: ["MIKRO", "KECIL", "MENENGAH", "BESAR"],
  })
  business_scale!: string;

  @ApiProperty({
    example: "Aktif",
    description: "Status aktif perusahaan dari public OSS RBA",
  })
  oss_status_aktif!: string;

  @ApiProperty({
    example: "OSS RBA",
    description: "Status migrasi perizinan dari public OSS RBA",
  })
  oss_status_migrasi!: string;

  @ApiProperty({
    example: "PMDN",
    description: "Status penanaman modal dari public OSS RBA",
  })
  oss_status_penanaman_modal!: string;

  @ApiProperty({
    example: "COMPLIANT",
    enum: ["COMPLIANT", "NON_COMPLIANT", "UNKNOWN"],
  })
  compliance_status!: string;

  @ApiProperty({ example: "2021-07-10", format: "date" })
  registered_date!: string;

  @ApiProperty({ type: [String], example: ["SNI 01-2973-2011", "Halal MUI"] })
  certifications!: string[];

  @ApiProperty({
    example: false,
    description: "True when the public OSS NIB endpoint returned usable data",
  })
  oss_public_verified!: boolean;

  @ApiProperty({
    example: {},
    description: "Raw public OSS NIB response retained for audit/debug",
  })
  oss_public_data!: Record<string, unknown>;

  @ApiProperty({
    type: [String],
    example: ["badanperizinan", "oss_public"],
    description: "Data sources used to assemble the final NIB result",
  })
  verification_sources!: string[];

  @ApiProperty({
    example: false,
    description: "True when OSS API was unavailable and data is simulated",
  })
  sandbox_mode!: boolean;
}
