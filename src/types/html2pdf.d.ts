declare module "html2pdf.js" {
  interface Html2PdfOptions {
    margin?: number | number[];
    filename?: string;
    image?: {
      type?: "jpeg" | "png" | "webp";
      quality?: number;
    };
    html2canvas?: {
      scale?: number;
      useCORS?: boolean;
      logging?: boolean;
    };
    jsPDF?: {
      unit?: string;
      format?: string;
      orientation?: "portrait" | "landscape";
    };
    pagebreak?: {
      mode?: string | string[];
      before?: string | string[];
      after?: string | string[];
      avoid?: string | string[];
    };
  }

  interface Html2PdfWorker {
    set(opt: Html2PdfOptions): Html2PdfWorker;
    from(element: HTMLElement | string): Html2PdfWorker;
    save(): Promise<void>;
    outputPdf(type?: string): Promise<any>;
    output(type?: string, options?: any): Promise<any>;
  }

  function html2pdf(): Html2PdfWorker;
  function html2pdf(
    element: HTMLElement,
    opt?: Html2PdfOptions
  ): Html2PdfWorker;

  export default html2pdf;
}
