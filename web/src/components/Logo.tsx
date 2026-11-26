import lens from "../../images/branding/favicon.svg";

export default function Logo({ className }: { className?: string }) {
  return <img src={lens} alt="" aria-hidden="true" className={className} />;
}
