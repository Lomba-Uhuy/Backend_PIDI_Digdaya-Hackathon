import { Body, Controller, Get, HttpCode, HttpStatus, Post } from "@nestjs/common";
import { ApiOkResponse, ApiOperation, ApiTags } from "@nestjs/swagger";
import { DocumentChecklistService } from "./document-checklist.service.js";
import { GenerateDocsDto } from "./dto/generate-docs.dto.js";

@ApiTags("Document Checklist")
@Controller("documents")
export class DocumentChecklistController {
  constructor(private readonly svc: DocumentChecklistService) {}

  @Get("checklist")
  @ApiOperation({
    summary: "Get the standard export document checklist",
  })
  base() {
    return { items: this.svc.baseChecklist() };
  }

  @Post("generate")
  @HttpCode(HttpStatus.OK)
  @ApiOperation({
    summary: "Generate official export documents dynamically",
    description: "Compiles detailed text content for commercial invoice, packing list, bill of lading, PEB, and COO.",
  })
  @ApiOkResponse({
    description: "List of generated export documents with custom contents",
  })
  async generateDocs(@Body() body: GenerateDocsDto) {
    const docs = await this.svc.generateDocuments(
      body.productId,
      body.umkmId,
      body.agreedPrice,
      body.quantity ?? 18.0,
      body.buyerName,
      body.buyerLocation,
      body.buyerCountry,
    );
    return { documents: docs };
  }
}