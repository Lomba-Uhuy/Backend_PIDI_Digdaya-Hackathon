import { Body, Controller, Post } from "@nestjs/common";
import { ApiBody, ApiOkResponse, ApiTags } from "@nestjs/swagger";
import { VerifyNibDto } from "./dto/verify-nib.dto.js";
import { NibVerificationService } from "./nib-verification.service.js";

const verifyNibExample = { nib: "1234567890" };

const verifyNibResponseExample = {
  nib: "1234567890",
  is_valid: true,
  business_name: "Demo UMKM NIB-7890",
  kbli: "",
  kbli_description: "",
  business_scale: "KECIL",
  oss_status_aktif: "Aktif",
  oss_status_migrasi: "OSS RBA",
  oss_status_penanaman_modal: "PMDN",
  compliance_status: "COMPLIANT",
  registered_date: "2022-01-15",
  certifications: [],
  npwp: "000000000000000",
  insw_verified: false,
  insw_kategori: "",
  insw_history: [],
  oss_public_verified: false,
  oss_public_data: {},
  verification_sources: ["sandbox"],
  sandbox_mode: true,
};

@ApiTags("NIB Verification")
@Controller("nib")
export class NibVerificationController {
  constructor(private readonly service: NibVerificationService) {}

  @Post("verify")
  @ApiBody({
    type: VerifyNibDto,
    examples: { default: { value: verifyNibExample } },
  })
  @ApiOkResponse({
    description:
      "Status legalitas NIB dari OSS RBA. " +
      "Hasil menggabungkan badanperizinan.co.id dan OSS public NIB endpoint bila kredensial tersedia. " +
      "sandbox_mode=true berarti semua sumber eksternal tidak tersedia dan data adalah simulasi.",
    schema: { example: verifyNibResponseExample },
  })
  verify(@Body() dto: VerifyNibDto) {
    return this.service.verify(dto.nib);
  }
}
